import cv2
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def analyze_visual_energy(video_path: str, sample_interval: float = 2.0) -> Dict[str, Any]:
    """
    Analyze video for motion energy and camera scene transitions.
    Uses direct frame seeking (cap.set) so we NEVER decode frames we don't need.
    sample_interval=2.0 means one sample every 2 seconds.
    Returns:
      - timeline: list of sampled energy values
      - scene_cuts: list of timestamps where abrupt scene transitions occur
    """
    timeline = []
    scene_cuts = []
    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("OpenCV could not open video")
            return {"timeline": [], "scene_cuts": []}

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
        total_duration = total_frames / fps if fps > 0 else 0

        prev_gray = None
        prev_hist = None

        t = 0.0
        while t <= total_duration + 0.1:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000)
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = round(t, 2)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [30, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist, 0, 1, cv2.NORM_MINMAX)

            energy = 0.0
            is_cut = False

            if prev_gray is not None and prev_hist is not None:
                diff = cv2.absdiff(gray, prev_gray)
                energy = float(np.mean(diff)) / 255.0
                hist_dist = cv2.compareHist(hist, prev_hist, cv2.HISTCMP_BHATTACHARYYA)
                if hist_dist > 0.45 or energy > 0.25:
                    is_cut = True
                    scene_cuts.append(timestamp)

            timeline.append({
                "timestamp": timestamp,
                "visual_energy": round(energy, 3),
                "is_cut": is_cut
            })
            prev_gray = gray
            prev_hist = hist
            t += sample_interval

        cap.release()
        logger.info(f"Visual analysis done: {len(timeline)} samples, {len(scene_cuts)} scene cuts detected")
    except Exception as e:
        logger.error(f"Visual analysis failed: {e}")
        return {"timeline": [], "scene_cuts": []}

    return {"timeline": timeline, "scene_cuts": scene_cuts}
