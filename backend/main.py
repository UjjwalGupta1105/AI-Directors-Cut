import os
import uuid
import logging
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import aiofiles

from models import JobState, JobStatus
from utils.job_store import create_job, get_job, update_job
from utils.file_manager import upload_path, output_path, UPLOADS_DIR, OUTPUTS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "your_gemini_api_key_here":
        logger.warning("⚠️  GEMINI_API_KEY is not set — analysis will fail")
    yield


app = FastAPI(title="AI Director's Cut", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    from services.video_service import is_supported_format

    if not is_supported_format(file.filename):
        raise HTTPException(400, "Unsupported format. Use .mp4, .mov, or .webm")

    job_id = str(uuid.uuid4())[:8]
    safe_name = f"{job_id}_{file.filename.replace(' ', '_')}"
    save_path = upload_path(safe_name)

    async with aiofiles.open(save_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)

    job = JobState(
        job_id=job_id,
        original_filename=file.filename,
        video_path=save_path,
        status=JobStatus.uploaded,
        message="Video uploaded successfully",
        progress=5,
    )
    create_job(job)
    logger.info(f"Uploaded: {file.filename} → job {job_id}")
    return {"job_id": job_id, "filename": file.filename}


@app.post("/api/process/{job_id}")
async def process_video(job_id: str, background_tasks: BackgroundTasks):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status not in (JobStatus.uploaded, JobStatus.failed):
        raise HTTPException(400, f"Job is already {job.status}")

    background_tasks.add_task(_run_pipeline, job_id)
    return {"status": "started", "job_id": job_id}


@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
    }


@app.get("/api/result/{job_id}")
async def get_result(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.completed:
        raise HTTPException(400, "Job not completed yet")

    output_filename = os.path.basename(job.output_path)
    return {
        "job_id": job.job_id,
        "original_filename": job.original_filename,
        "output_filename": output_filename,
        "duration": job.duration,
        "analysis": job.analysis.model_dump() if job.analysis else None,
    }


@app.get("/api/health")
async def health():
    return {"status": "ok", "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash")}


@app.get("/api/video/{filename}")
async def serve_video(filename: str):
    for directory in [UPLOADS_DIR, OUTPUTS_DIR]:
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            # FileResponse handles Accept-Ranges / byte-range requests natively
            return FileResponse(path, media_type="video/mp4")
    raise HTTPException(404, "Video not found")


def _run_pipeline(job_id: str):
    """Full processing pipeline run in a background thread."""
    job = get_job(job_id)
    if not job:
        return

    try:
        from services.analysis_service import analyze_visual_energy
        from services.gemini_service import analyze_video
        from services.video_service import get_duration, validate_clips
        from services.render_service import render_highlight_reel

        # Step 1 — Get video duration & OpenCV analysis
        update_job(job_id, status=JobStatus.analyzing, progress=10,
                   message="Analyzing video motion and scene cuts...")
        duration = get_duration(job.video_path)
        update_job(job_id, duration=duration)

        visual_data = analyze_visual_energy(job.video_path)
        sample_count = len(visual_data.get("timeline", [])) if isinstance(visual_data, dict) else len(visual_data)
        logger.info(f"Visual timeline: {sample_count} samples, duration: {duration:.2f}s")

        # Step 2 — Gemini video understanding
        update_job(job_id, progress=20, message="Preparing video & analyzing with Gemini AI...")
        
        import threading
        # Show incremental progress while Gemini upload/analysis runs in background
        _upload_done = threading.Event()
        def _tick_progress():
            steps = [
                (25, "Uploading video to Gemini AI..."),
                (32, "Gemini AI processing visual scenes..."),
                (40, "AI analyzing scene content & highlight moments..."),
                (46, "Refining moment boundaries & cinematic scores..."),
            ]
            for progress, msg in steps:
                if _upload_done.wait(timeout=4):
                    break
                update_job(job_id, progress=progress, message=msg)
        
        tick_thread = threading.Thread(target=_tick_progress, daemon=True)
        tick_thread.start()
        
        analysis = analyze_video(job.video_path, visual_data, duration=duration)
        _upload_done.set()
        logger.info(f"Gemini found {len(analysis.clips)} clips")

        update_job(job_id, status=JobStatus.selecting, progress=50,
                   message="Optimizing clip boundaries & scene cuts...")

        # Step 3 — Validate timestamps
        valid_clips = validate_clips(analysis.clips, duration)

        if not valid_clips:
            raise RuntimeError("No valid clips after timestamp validation")

        analysis.clips = valid_clips
        update_job(job_id, analysis=analysis)

        # Step 4 — TTS narration
        update_job(job_id, status=JobStatus.generating_audio, progress=60,
                   message="Generating AI voiceover narration...")

        # Step 5 — Render (TTS happens inside render_highlight_reel)
        def _on_render_start():
            update_job(job_id, status=JobStatus.rendering, progress=75,
                       message="Rendering video, mixing audio & applying dynamic overlays...")

        final_path = render_highlight_reel(
            job_id=job_id,
            source_video=job.video_path,
            clips=valid_clips,
            intro_text=analysis.intro,
            outro_text=analysis.outro,
            video_title=analysis.title,
            video_summary=analysis.summary,
            on_render_start=_on_render_start,
        )

        if not os.path.exists(final_path):
            raise RuntimeError("Rendered file not found")

        update_job(
            job_id,
            status=JobStatus.completed,
            progress=100,
            message="Your highlight reel is ready!",
            output_path=final_path,
        )
        logger.info(f"Pipeline complete for job {job_id}: {final_path}")

    except Exception as e:
        logger.exception(f"Pipeline failed for job {job_id}")
        err_msg = str(e)
        if "503" in err_msg or "UNAVAILABLE" in err_msg or "high demand" in err_msg.lower():
            err_msg = "Google Gemini is currently experiencing a temporary demand spike (503). Automatic model fallbacks and backoffs are enabled; please click 'Start over' and try again in a moment."
        elif "RESOURCE_EXHAUSTED" in err_msg or "429" in err_msg:
            err_msg = "Gemini API rate limit reached (429 Resource Exhausted). Please wait a moment and try again."

        update_job(
            job_id,
            status=JobStatus.failed,
            message="Processing failed",
            error=err_msg,
        )
