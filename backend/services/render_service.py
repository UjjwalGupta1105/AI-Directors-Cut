import subprocess
import os
import logging
from typing import List, Optional, Callable
from models import ClipInfo
from utils.file_manager import temp_path, output_path, find_background_music
from services.video_service import get_duration, get_dimensions, has_audio_stream
from services.overlay_service import create_intro_overlay, create_moment_overlay, create_outro_overlay

logger = logging.getLogger(__name__)


def _run_ffmpeg(args: List[str], label: str):
    cmd = ["ffmpeg", "-y"] + args
    logger.info(f"FFmpeg [{label}]: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=360)
    if result.returncode != 0:
        logger.error(f"FFmpeg [{label}] stderr: {result.stderr[-2000:]}")
        raise RuntimeError(f"FFmpeg failed ({label}): {result.stderr[-500:]}")
    return result


def cut_clip(source: str, start: float, end: float, out_path: str):
    """Cut a clip using fast stream-copy (no re-encode) for maximum speed."""
    has_audio = has_audio_stream(source)
    if has_audio:
        # -ss before -i = fast seek; stream copy = no re-encode
        _run_ffmpeg([
            "-ss", str(start),
            "-to", str(end),
            "-i", source,
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            out_path
        ], "cut_clip")
    else:
        clip_dur = max(0.1, end - start)
        _run_ffmpeg([
            "-ss", str(start),
            "-to", str(end),
            "-i", source,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "copy", "-c:a", "aac",
            "-t", str(clip_dur),
            "-avoid_negative_ts", "make_zero",
            out_path
        ], "cut_clip_no_audio")


def concatenate_clips(clip_paths: List[str], out_path: str):
    """Concatenate individual highlight clips using fast stream-copy."""
    concat_list = temp_path(f"concat_list_{os.path.basename(out_path)}.txt")
    with open(concat_list, "w") as f:
        for p in clip_paths:
            p_escaped = p.replace("\\", "/")
            f.write(f"file '{p_escaped}'\n")

    _run_ffmpeg([
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        out_path
    ], "concatenate")


def mix_video_audio_and_overlays(
    video_path: str,
    intro_audio: Optional[str],
    outro_audio: Optional[str],
    music_path: Optional[str],
    overlay_configs: List[dict],
    out_path: str
):
    """
    Mix narration audio and dynamic graphic overlays into the final video.
    Ensures:
      1. Original video audio starts at t=0 and remains 100% in sync with video frames.
      2. Intro voiceover overlays start of video (t=0.3s).
      3. Outro voiceover overlays end of video (delayed to end of video).
      4. Background music looped at low volume under narration and video.
      5. Dynamic visual overlays enabled for specified time windows.
    """
    total_dur = get_duration(video_path)
    if total_dur <= 0:
        total_dur = 10.0

    has_intro = bool(intro_audio and os.path.exists(intro_audio))
    has_outro = bool(outro_audio and os.path.exists(outro_audio))
    has_music = bool(music_path and os.path.exists(music_path))
    video_has_audio = has_audio_stream(video_path)

    intro_dur = get_duration(intro_audio) if has_intro else 0.0
    outro_dur = get_duration(outro_audio) if has_outro else 0.0

    inputs = ["-i", video_path]
    current_input_idx = 1

    # Add overlay image inputs
    overlay_input_indices = []
    for cfg in overlay_configs:
        png_path = cfg["path"]
        if os.path.exists(png_path):
            inputs += ["-i", png_path]
            overlay_input_indices.append((current_input_idx, cfg["start"], cfg["end"]))
            current_input_idx += 1

    # Add audio inputs
    intro_idx = None
    if has_intro:
        inputs += ["-i", intro_audio]
        intro_idx = current_input_idx
        current_input_idx += 1

    outro_idx = None
    if has_outro:
        inputs += ["-i", outro_audio]
        outro_idx = current_input_idx
        current_input_idx += 1

    music_idx = None
    if has_music:
        inputs += ["-i", music_path]
        music_idx = current_input_idx
        current_input_idx += 1

    filter_chains = []

    # 1. Video Overlays filtergraph
    last_v = "0:v"
    for i, (ov_idx, s_time, e_time) in enumerate(overlay_input_indices):
        next_v = f"v_ov_{i}"
        filter_chains.append(
            f"[{last_v}][{ov_idx}:v]overlay=x=0:y=0:enable='between(t,{s_time:.2f},{e_time:.2f})'[{next_v}]"
        )
        last_v = next_v
    final_v = last_v

    # 2. Audio Processing filtergraph
    # Base video audio (ducked to 0.40 so narration and speech is crystal clear)
    if video_has_audio:
        filter_chains.append("[0:a]volume=0.45[vid_audio]")
    else:
        filter_chains.append(f"aevalsrc=0:d={total_dur}[vid_audio]")

    audio_mix_inputs = ["[vid_audio]"]

    # Intro narration with small 0.3s lead-in delay
    if has_intro:
        filter_chains.append(f"[{intro_idx}:a]adelay=300|300,volume=1.0[intro_a]")
        audio_mix_inputs.append("[intro_a]")

    # Outro narration delayed to the tail of the video
    if has_outro:
        # Start outro so it finishes right before the video ends (with 0.5s margin)
        target_outro_start = max(0.5, total_dur - outro_dur - 0.5)
        outro_delay_ms = int(target_outro_start * 1000)
        filter_chains.append(f"[{outro_idx}:a]adelay={outro_delay_ms}|{outro_delay_ms},volume=1.0[outro_a]")
        audio_mix_inputs.append("[outro_a]")

    # Background music with loop and end fade-out
    if has_music:
        fade_start = max(0.0, total_dur - 2.5)
        filter_chains.append(
            f"[{music_idx}:a]volume=0.08,aloop=loop=-1:size=2e+09,afade=t=out:st={fade_start:.2f}:d=2.0[music_track]"
        )
        audio_mix_inputs.append("[music_track]")

    # Mix all audio tracks in parallel
    num_audio = len(audio_mix_inputs)
    filter_chains.append(
        f"{''.join(audio_mix_inputs)}amix=inputs={num_audio}:duration=first:dropout_transition=2[final_a]"
    )

    filter_complex = ";".join(filter_chains)

    _run_ffmpeg(
        inputs + [
            "-filter_complex", filter_complex,
            "-map", f"[{final_v}]" if final_v != "0:v" else "0:v",
            "-map", "[final_a]",
            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23",
            "-c:a", "aac",
            "-t", str(total_dur),
            out_path
        ],
        "mix_video_audio_overlays"
    )


def render_highlight_reel(
    job_id: str,
    source_video: str,
    clips: List[ClipInfo],
    intro_text: str,
    outro_text: str,
    video_title: str = "Highlight Reel",
    video_summary: str = "",
    on_render_start: Optional[Callable] = None,
) -> str:
    import concurrent.futures
    from services.tts_service import generate_narration

    # Step A: Cut each clip (fast stream-copy)
    clip_paths = []
    for i, clip in enumerate(clips):
        clip_out = temp_path(f"{job_id}_clip_{i}.mp4")
        cut_clip(source_video, clip.start, clip.end, clip_out)
        clip_paths.append(clip_out)

    # Step B: Concatenate (fast stream-copy)
    concat_out = temp_path(f"{job_id}_concat.mp4")
    concatenate_clips(clip_paths, concat_out)

    # Step C: Generate intro + outro TTS in parallel (saves ~50% TTS time)
    intro_wav = None
    outro_wav = None

    def _gen_intro():
        if intro_text.strip():
            path = temp_path(f"{job_id}_intro.wav")
            return generate_narration(intro_text, path)
        return None

    def _gen_outro():
        if outro_text.strip():
            path = temp_path(f"{job_id}_outro.wav")
            return generate_narration(outro_text, path)
        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        fut_intro = pool.submit(_gen_intro)
        fut_outro = pool.submit(_gen_outro)
        intro_wav = fut_intro.result()
        outro_wav = fut_outro.result()

    if on_render_start:
        on_render_start()

    # Step D: Generate dynamic visual overlays
    width, height = get_dimensions(concat_out)
    total_dur = get_duration(concat_out)
    overlay_configs = []

    # 1. Intro overlay
    intro_png = temp_path(f"{job_id}_overlay_intro.png")
    create_intro_overlay(width, height, video_title, intro_png, subtitle=video_summary)
    overlay_configs.append({
        "path": intro_png,
        "start": 0.4,
        "end": min(4.5, total_dur - 0.5)
    })

    # 2. Moment overlays for each clip in the concatenated reel
    curr_time = 0.0
    for i, clip in enumerate(clips):
        clip_dur = max(0.5, clip.end - clip.start)
        moment_png = temp_path(f"{job_id}_overlay_moment_{i}.png")
        create_moment_overlay(
            width=width,
            height=height,
            moment_idx=i + 1,
            total_moments=len(clips),
            score=clip.score,
            moment_title=clip.overlay_title or f"Highlight Moment {i + 1}",
            reason=clip.reason,
            output_png=moment_png
        )
        overlay_configs.append({
            "path": moment_png,
            "start": round(curr_time + 0.3, 2),
            "end": round(curr_time + min(4.0, clip_dur - 0.2), 2)
        })
        curr_time += clip_dur

    # 3. Outro overlay
    outro_png = temp_path(f"{job_id}_overlay_outro.png")
    create_outro_overlay(width, height, video_title, outro_png, subtitle=video_summary)
    overlay_configs.append({
        "path": outro_png,
        "start": max(0.5, round(total_dur - 4.5, 2)),
        "end": round(total_dur, 2)
    })

    # Step E: Background music
    music = find_background_music()
    if music:
        logger.info(f"Using background music track: {music}")

    # Step F: Final render mix
    final_out = output_path(f"{job_id}_highlight.mp4")
    mix_video_audio_and_overlays(
        video_path=concat_out,
        intro_audio=intro_wav,
        outro_audio=outro_wav,
        music_path=music,
        overlay_configs=overlay_configs,
        out_path=final_out
    )

    return final_out
