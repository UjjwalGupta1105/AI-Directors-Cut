import os
import json
import time
import logging
import re
from typing import List, Dict, Any, Optional, Set
from google import genai
from google.genai import types
from models import AnalysisResult, ClipInfo

logger = logging.getLogger(__name__)

_client = None
_exhausted_models: Set[str] = set()  # Track quota-exhausted models to skip immediately


def get_client() -> genai.Client:
    global _client
    from dotenv import load_dotenv
    from pathlib import Path
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(dotenv_path=env_path, override=True)

    api_key = os.getenv("GEMINI_API_KEY", "").strip().strip('"').strip("'")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    if _client is None or getattr(_client, "_cached_key", None) != api_key:
        _client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=120000))
        _client._cached_key = api_key
    return _client


def _build_prompt(duration: float, scene_info: str) -> str:
    """Build a strong, duration-aware prompt for the Gemini model."""
    if duration >= 300:
        num_clips, min_total, max_total, min_clip, max_clip = 7, int(duration * 0.30), int(duration * 0.45), 10, 22
    elif duration >= 180:
        num_clips, min_total, max_total, min_clip, max_clip = 6, int(duration * 0.32), int(duration * 0.48), 9, 20
    elif duration >= 90:
        num_clips, min_total, max_total, min_clip, max_clip = 5, int(duration * 0.35), int(duration * 0.50), 8, 18
    elif duration >= 45:
        num_clips, min_total, max_total, min_clip, max_clip = 4, int(duration * 0.40), int(duration * 0.55), 7, 16
    else:
        num_clips, min_total, max_total, min_clip, max_clip = 3, int(duration * 0.50), int(duration * 0.70), 5, 12

    return f"""You are an expert cinematic video editor and producer. Create a PROFESSIONAL highlight reel from this {duration:.1f}-second video.

TOTAL VIDEO DURATION: {duration:.2f} seconds ({duration/60:.1f} minutes).
{scene_info}

═══ CRITICAL REQUIREMENT: INTRO & OUTRO MUST BE ABOUT THE VIDEO ═══
- The title, intro narration, outro narration, clip titles, and reasons MUST BE 100% ABOUT THE ACTUAL CONTENT, SUBJECT, OR TOPIC OF THE VIDEO ITSELF.
- NEVER talk about "AI Director's Cut", "our platform", "this editing tool", or "this highlight reel tour".
- Speak directly as a knowledgeable narrator introducing and concluding the topic discussed or shown in the footage (e.g. tech tutorial, keynote, podcast, interview, or demonstration).

═══ MANDATORY CLIPPING RULES ═══

1. CLIP COUNT: Select exactly {num_clips} clips.

2. CLIP LENGTH: Each clip MUST be between {min_clip} and {max_clip} seconds long.
   - NEVER create a clip shorter than {min_clip} seconds.
   - Each clip must capture a complete, coherent discussion, action, or insight.

3. TOTAL REEL LENGTH: Sum of all clip durations MUST be between {min_total} and {max_total} seconds.
   - For a {duration:.0f}s video you MUST produce at least {min_total}s of highlights.

4. FULL COVERAGE: Distribute clips across the ENTIRE video timeline:
   - Clip 1 from the 1st 1/{num_clips} of the video
   - Clip 2 from the 2nd 1/{num_clips} of the video
   - ... through Clip {num_clips} from near the end.
   - Do NOT cluster clips at the beginning.

5. TIMESTAMPS:
   - All within 0.0 to {duration:.2f}
   - Strictly chronological: clip[i].start < clip[i+1].start
   - No overlaps: clip[i].end <= clip[i+1].start
   - Add 0.3s buffer before/after dialogue

6. PER-CLIP METADATA:
   - "overlay_title": 2-4 word title describing what is happening or discussed in this specific moment of the video
   - "reason": specific explanation of what insight, action, or value this moment provides to the viewer
   - "category": one of ["Introduction", "Key Discussion", "Deep Dive", "Core Insight", "Demonstration", "Takeaway"]
   - "score": integer 8-10

7. SPOKEN NARRATION & VIDEO INFO:
   - "title": A descriptive, catchy title capturing what the video is actually about (e.g. "Demystifying Modern Cloud Architecture" or "Insights on Modern Engineering"). NEVER call it "AI Director's Cut" or "Highlight Reel".
   - "summary": 2 concise sentences summarizing the main theme and key message of the video.
   - "intro": 2-3 engaging, conversational spoken sentences introducing what THIS specific video is about and what the viewer is about to see/learn. (e.g. "In this session, we dive into... Discover how..."). NEVER say "Welcome to AI Director's Cut" or "Welcome to this highlight reel".
   - "outro": 1-2 thoughtful spoken concluding sentences summarizing the key takeaway or final thought of this video. (e.g. "From core principles to practical takeaways, that wraps up this overview. Thank you for watching!"). NEVER mention the editing tool or platform.

Return ONLY valid JSON with NO markdown, NO code fences, NO extra text:

{{
  "title": "Descriptive Topic Title of the Video",
  "summary": "Concise 2-sentence summary of the video's actual content.",
  "clips": [
    {{
      "start": 5.0,
      "end": 18.5,
      "overlay_title": "Core Discussion",
      "reason": "Clear explanation of the primary subject matter.",
      "score": 9,
      "category": "Key Discussion"
    }}
  ],
  "intro": "In this video, we explore the core principles and key moments...",
  "outro": "Those were the primary insights and takeaways from this session. Thank you for watching!",
  "editing_notes": [
    "Distributed {num_clips} highlights proportionally across {duration:.0f}s."
  ]
}}"""


def _extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON object from within text
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            return json.loads(match.group())
        raise


def _validate_and_fix_clips(clips: list, duration: float, num_clips: int,
                             min_clip: float, max_clip: float) -> list:
    """Post-process Gemini clips to enforce duration constraints."""
    if not clips:
        return clips
    fixed = []
    prev_end = 0.0
    for i, c in enumerate(clips):
        start = max(float(c.get("start", 0)), prev_end + 0.1)
        end = float(c.get("end", start + min_clip))
        clip_len = end - start
        # Extend clip if too short
        if clip_len < min_clip:
            end = min(duration - 0.1, start + min_clip)
            logger.info(f"Extended clip {i} from {clip_len:.1f}s to {end - start:.1f}s")
        # Trim if too long
        if end - start > max_clip:
            end = start + max_clip
        # Enforce bounds
        end = min(end, duration - 0.1)
        if end - start < 3.0:
            logger.warning(f"Skipping clip {i}: too short after fix ({start:.1f}-{end:.1f})")
            continue
        fixed.append({**c, "start": round(start, 2), "end": round(end, 2)})
        prev_end = end
    return fixed


def _repair_json_with_gemini(client: genai.Client, bad_text: str, model: str) -> dict:
    repair_prompt = f"""The following text was supposed to be valid JSON but is malformed. Fix it and return ONLY the corrected JSON with no extra text or markdown.\n\n{bad_text}"""
    response = client.models.generate_content(
        model=model,
        contents=repair_prompt
    )
    return _extract_json(response.text)


def create_video_proxy(video_path: str) -> str:
    """
    If the video file is larger than 12MB, create a lightweight 480p proxy
    for ultra-fast uploading to Gemini AI (<3s vs >2min).
    The final video rendering always uses the original full-quality file.
    """
    import subprocess
    try:
        if not os.path.exists(video_path):
            return video_path
        size_mb = os.path.getsize(video_path) / (1024 * 1024)
        if size_mb <= 12:
            return video_path

        proxy_path = os.path.join(
            os.path.dirname(video_path),
            f"proxy_{os.path.basename(video_path)}"
        )
        if os.path.exists(proxy_path) and os.path.getsize(proxy_path) > 1000:
            return proxy_path

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", "scale=-2:480",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "30",
            "-c:a", "aac",
            "-b:a", "64k",
            proxy_path
        ]
        logger.info(f"Generating lightweight analysis proxy for {size_mb:.1f}MB video...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        if os.path.exists(proxy_path):
            proxy_size = os.path.getsize(proxy_path) / (1024 * 1024)
            logger.info(f"Proxy created: {proxy_size:.1f}MB (original was {size_mb:.1f}MB)")
            return proxy_path
    except Exception as e:
        logger.warning(f"Failed to create proxy video, using original: {e}")
    return video_path


def upload_video_to_gemini(video_path: str) -> types.File:
    client = get_client()
    upload_target = create_video_proxy(video_path)
    logger.info(f"Uploading video to Gemini Files API: {upload_target}")

    with open(upload_target, "rb") as f:
        uploaded = client.files.upload(
            file=f,
            config=types.UploadFileConfig(
                mime_type="video/mp4",
                display_name=os.path.basename(upload_target)
            )
        )

    # Poll until ACTIVE
    polls = 0
    while uploaded.state.name == "PROCESSING" and polls < 60:
        logger.info("Waiting for Gemini file to be ready...")
        time.sleep(2.0)
        uploaded = client.files.get(name=uploaded.name)
        polls += 1

    if uploaded.state.name != "ACTIVE":
        raise RuntimeError(f"Gemini file upload failed with state: {uploaded.state.name}")

    logger.info(f"File ready: {uploaded.name}")
    return uploaded


def _generate_fallback_analysis(visual_data: Any, duration: float) -> AnalysisResult:
    """Robust algorithmic highlight generation covering the full video timeline."""
    logger.warning("Generating algorithmic highlight reel across entire video timeline...")
    dur = duration if duration > 10.0 else 60.0
    clips: List[ClipInfo] = []

    scene_cuts: List[float] = []
    timeline: List[dict] = []
    if isinstance(visual_data, dict):
        scene_cuts = visual_data.get("scene_cuts", [])
        timeline = visual_data.get("timeline", [])

    # Scale clip count and length based on video duration
    if dur >= 300:
        num_clips, target_clip_len = 7, 18.0
    elif dur >= 180:
        num_clips, target_clip_len = 6, 16.0
    elif dur >= 90:
        num_clips, target_clip_len = 5, 14.0
    elif dur >= 45:
        num_clips, target_clip_len = 4, 12.0
    else:
        num_clips, target_clip_len = 3, 10.0

    zone_duration = dur / num_clips

    titles = [
        "Opening Keynote",
        "Core Concept",
        "In-Depth Discussion",
        "Critical Insight",
        "Key Demonstration",
        "Actionable Analysis",
        "Final Summary"
    ]
    reasons = [
        "Opening sequence introducing the primary theme, context, and focus of the video.",
        "Comprehensive walkthrough of the fundamental subject matter and core ideas.",
        "Detailed examination addressing crucial observations, technical details, and nuance.",
        "High-impact moment delivering practical insights and essential perspective.",
        "Core demonstration providing concrete clarity and real-world context.",
        "Actionable analysis presenting valuable strategic observations.",
        "Concluding segment synthesizing key lessons and central takeaways."
    ]
    categories = ["Introduction", "Core Concept", "Deep Dive", "Key Insight", "Demonstration", "Analysis", "Summary"]

    last_end = 0.0
    for i in range(num_clips):
        zone_start = i * zone_duration
        zone_end = min(dur, (i + 1) * zone_duration)
        chosen_start = max(last_end + 0.5, zone_start + 1.0)

        matching_cuts = [c for c in scene_cuts if zone_start <= c <= zone_end - 4.0 and c >= last_end + 0.5]
        if matching_cuts:
            chosen_start = matching_cuts[0]
        else:
            zone_samples = [s for s in timeline if zone_start <= s.get("timestamp", 0) <= zone_end
                            and s.get("timestamp", 0) >= last_end + 0.5]
            if zone_samples:
                best = max(zone_samples, key=lambda s: s.get("visual_energy", 0))
                chosen_start = max(last_end + 0.5, best.get("timestamp", chosen_start) - 1.0)

        chosen_end = min(dur - 0.2, chosen_start + target_clip_len)
        if chosen_end - chosen_start >= 5.0:
            clips.append(ClipInfo(
                start=round(chosen_start, 2),
                end=round(chosen_end, 2),
                reason=reasons[min(i, len(reasons) - 1)],
                score=9 - (i % 2),
                overlay_title=titles[min(i, len(titles) - 1)],
                category=categories[min(i, len(categories) - 1)],
                type="highlight"
            ))
            last_end = chosen_end

    total_time = sum(c.end - c.start for c in clips)
    logger.info(f"Algorithmic highlights: {len(clips)} clips, {total_time:.1f}s reel from {dur:.1f}s video ({100*total_time/dur:.0f}% coverage)")

    return AnalysisResult(
        title="Featured Video Highlights",
        summary="An expertly curated highlight reel capturing the premier moments and key insights across the entire footage.",
        clips=clips,
        intro="In this video highlight reel, we explore the essential moments, key discussions, and defining insights from start to finish.",
        outro="Those were the primary takeaways and standout moments from this video. Thank you for watching!",
        editing_notes=[
            f"Distributed {len(clips)} highlights proportionally across the full {dur:.0f}s video.",
            f"Each clip is ~{target_clip_len:.0f}s for complete, coherent demonstrations.",
            "Applied scene transition detection and visual energy scoring for optimal cut points."
        ]
    )


def analyze_video(video_path: str, visual_data: Any, duration: float = 0.0) -> AnalysisResult:
    global _exhausted_models
    client = get_client()

    try:
        gemini_file = upload_video_to_gemini(video_path)
    except Exception as upload_err:
        logger.warning(f"Video upload to Gemini failed: {upload_err}. Using visual analysis fallback.")
        return _generate_fallback_analysis(visual_data, duration)

    scene_info = ""
    if isinstance(visual_data, dict):
        scene_cuts = visual_data.get("scene_cuts", [])
        if scene_cuts:
            scene_info = f"Detected visual scene transitions at: {scene_cuts[:20]} (seconds)"
        timeline = visual_data.get("timeline", [])
        high_energy = [t for t in timeline if t.get("visual_energy", 0) > 0.06][:15]
        if high_energy and not scene_info:
            scene_info = f"High motion timestamps: {[round(t['timestamp'], 1) for t in high_energy]}"

    dur_val = duration if duration > 0 else 60.0
    prompt = _build_prompt(dur_val, scene_info)

    # Compute expected clip params for post-validation
    if dur_val >= 90:
        num_clips_expected, min_clip_expected, max_clip_expected = 5, 8, 18
    elif dur_val >= 45:
        num_clips_expected, min_clip_expected, max_clip_expected = 4, 7, 16
    else:
        num_clips_expected, min_clip_expected, max_clip_expected = 3, 5, 12

    # Valid Gemini model IDs — prioritize tested working models first
    configured_model = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview").strip()
    candidate_models = [
        configured_model,
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
        "gemini-flash-lite-latest",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]
    # Deduplicate while preserving priority order, skip exhausted models
    models_to_try = []
    seen = set()
    for m in candidate_models:
        if m and m not in seen and m not in _exhausted_models:
            seen.add(m)
            models_to_try.append(m)

    if not models_to_try:
        logger.warning("All models are quota-exhausted. Using fallback.")
        return _generate_fallback_analysis(visual_data, duration)

    raw_text = ""
    data = None
    last_error = None

    for model_name in models_to_try:
        logger.info(f"Attempting video analysis with Gemini model: {model_name}")
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=[
                    types.Part.from_uri(file_uri=gemini_file.uri, mime_type="video/mp4"),
                    types.Part.from_text(text=prompt)
                ]
            )
            raw_text = response.text
            data = _extract_json(raw_text)
            if data and "clips" in data and len(data["clips"]) > 0:
                logger.info(f"\u2705 Analysis completed with model: {model_name} \u2014 {len(data['clips'])} clips found")
                break
            else:
                logger.warning(f"Model {model_name} returned empty clips, trying next...")
                data = None
        except (json.JSONDecodeError, ValueError) as json_err:
            logger.warning(f"Model {model_name}: JSON parse failed: {json_err}")
            try:
                data = _repair_json_with_gemini(client, raw_text, model_name)
                if data and "clips" in data and len(data["clips"]) > 0:
                    logger.info(f"\u2705 Analysis recovered via JSON repair on model: {model_name}")
                    break
            except Exception as repair_err:
                logger.warning(f"JSON repair failed: {repair_err}")
            data = None
        except Exception as e:
            err_msg = str(e)
            last_error = e
            logger.warning(f"Model {model_name} failed: {err_msg[:200]}")
            if any(x in err_msg for x in ["429", "RESOURCE_EXHAUSTED", "Quota exceeded", "quota"]):
                _exhausted_models.add(model_name)
                logger.info(f"Model {model_name} quota-exhausted, skipping immediately.")
            elif any(x in err_msg for x in ["404", "not found", "does not exist"]):
                logger.info(f"Model {model_name} not available, skipping.")
            else:
                logger.info(f"Model {model_name} error, trying next candidate...")

    if not data or "clips" not in data or len(data.get("clips", [])) == 0:
        logger.warning(f"All Gemini models failed. Using algorithmic fallback. (Last error: {last_error})")
        return _generate_fallback_analysis(visual_data, duration)

    # Post-process: enforce duration constraints on Gemini-returned clips
    raw_clips = data.get("clips", [])
    fixed_clips_data = _validate_and_fix_clips(
        raw_clips, dur_val,
        num_clips_expected, min_clip_expected, max_clip_expected
    )

    if len(fixed_clips_data) < 2:
        logger.warning("Too few valid clips after post-processing. Using fallback.")
        return _generate_fallback_analysis(visual_data, duration)

    clips = []
    for c in fixed_clips_data:
        start_t = float(c["start"])
        end_t = float(c["end"])
        if start_t < end_t:
            clips.append(ClipInfo(
                start=start_t,
                end=end_t,
                reason=c.get("reason", "Key highlight moment"),
                score=int(c.get("score", 8)),
                overlay_title=c.get("overlay_title", "Highlight Moment"),
                category=c.get("category", "Highlight"),
                type="highlight"
            ))

    if not clips:
        return _generate_fallback_analysis(visual_data, duration)

    total_reel = sum(c.end - c.start for c in clips)
    logger.info(f"Final reel: {len(clips)} clips, {total_reel:.1f}s total ({100*total_reel/dur_val:.0f}% of {dur_val:.0f}s video)")

    return AnalysisResult(
        title=data.get("title", "Highlight Reel"),
        summary=data.get("summary", ""),
        clips=clips,
        intro=data.get("intro", ""),
        outro=data.get("outro", ""),
        editing_notes=data.get("editing_notes", [])
    )

