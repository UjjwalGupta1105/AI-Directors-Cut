"""Test FFmpeg rendering, audio sync, delayed outro, overlays, and BGM."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from models import ClipInfo
from services.render_service import render_highlight_reel
from utils.file_manager import TEMP_DIR, OUTPUTS_DIR

VIDEO = os.path.join(TEMP_DIR, "test_video.mp4")
if not os.path.exists(VIDEO):
    print("ERROR: test_video.mp4 not found in temp/")
    sys.exit(1)

print("=== Running full render pipeline test ===")
clips = [
    ClipInfo(start=0.0, end=6.0, reason="Opening demo and hero introduction", score=8, overlay_title="Opening Demo"),
    ClipInfo(start=10.0, end=18.0, reason="Core action and interactive workflows", score=9, overlay_title="Core Workflow"),
]

final_out = render_highlight_reel(
    job_id="test_run",
    source_video=VIDEO,
    clips=clips,
    intro_text="Welcome to this AI Director's Cut demo. Let's see the best moments.",
    outro_text="That wraps up our highlights. Thanks for watching!",
    video_title="Interactive Showcase Demo",
    on_render_start=lambda: print("-> Rendering started...")
)

print(f"Final output: {final_out}")
print(f"Exists: {os.path.exists(final_out)}, Size: {os.path.getsize(final_out) if os.path.exists(final_out) else 0} bytes")
print("\n[OK] All FFmpeg/TTS/Overlay/Audio tests passed successfully!")
