import subprocess
import json
import logging
import os
from typing import List, Tuple
from models import ClipInfo

logger = logging.getLogger(__name__)


def get_video_info(video_path: str) -> dict:
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        raise RuntimeError(f"FFprobe failed: {result.stderr}")
    return json.loads(result.stdout)


def get_duration(video_path: str) -> float:
    info = get_video_info(video_path)
    duration = float(info.get("format", {}).get("duration", 0))
    if duration == 0:
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "video":
                duration = float(stream.get("duration", 0))
                break
    return duration


def get_dimensions(video_path: str) -> Tuple[int, int]:
    info = get_video_info(video_path)
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video":
            w = int(stream.get("width", 1280))
            h = int(stream.get("height", 720))
            return (w, h)
    return (1280, 720)


def has_audio_stream(video_path: str) -> bool:
    try:
        info = get_video_info(video_path)
        for stream in info.get("streams", []):
            if stream.get("codec_type") == "audio":
                return True
    except Exception as e:
        logger.warning(f"Failed to inspect audio stream: {e}")
    return False


def validate_clips(clips: List[ClipInfo], duration: float) -> List[ClipInfo]:
    """Validate, sort, and resolve overlaps in clip selections."""
    raw_sorted = sorted(clips, key=lambda c: c.start)
    valid: List[ClipInfo] = []

    for clip in raw_sorted:
        if clip.start >= clip.end:
            logger.warning(f"Rejecting clip: start={clip.start} >= end={clip.end}")
            continue
        if clip.start >= duration:
            logger.warning(f"Rejecting clip: start={clip.start} >= duration={duration}")
            continue

        clamped_start = max(clip.start, 0.0)
        clamped_end = min(clip.end, duration - 0.05)

        # Resolve overlap with previously accepted clip
        if valid and clamped_start < valid[-1].end:
            clamped_start = valid[-1].end + 0.1

        if clamped_end - clamped_start < 2.0:
            logger.warning(f"Rejecting clip: too short after boundary resolution ({clamped_start}-{clamped_end})")
            continue

        valid.append(ClipInfo(
            start=round(clamped_start, 2),
            end=round(clamped_end, 2),
            reason=clip.reason,
            score=clip.score,
            overlay_title=clip.overlay_title or "Key Highlight",
            category=clip.category or "Highlight",
            type="highlight"
        ))

    return valid


def is_supported_format(filename: str) -> bool:
    return filename.lower().endswith((".mp4", ".mov", ".webm"))
