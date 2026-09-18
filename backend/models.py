from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


class JobStatus(str, Enum):
    uploaded = "uploaded"
    analyzing = "analyzing"
    selecting = "selecting"
    generating_audio = "generating_audio"
    rendering = "rendering"
    completed = "completed"
    failed = "failed"


class ClipInfo(BaseModel):
    start: float
    end: float
    reason: str
    score: int
    type: Optional[str] = "highlight"
    overlay: Optional[str] = None
    overlay_type: Optional[str] = "highlight"
    overlay_title: Optional[str] = None
    category: Optional[str] = "Highlight"
    caption: Optional[str] = None


class AnalysisResult(BaseModel):
    title: str
    summary: str
    content_type: Optional[str] = "general"
    music_mood: Optional[str] = "calm"
    clips: List[ClipInfo]
    intro: str
    outro: str
    editing_notes: List[str]


class JobState(BaseModel):
    job_id: str
    status: JobStatus = JobStatus.uploaded
    progress: int = 0
    message: str = "Video uploaded successfully"
    original_filename: str = ""
    video_path: str = ""
    output_path: str = ""
    analysis: Optional[AnalysisResult] = None
    error: Optional[str] = None
    duration: Optional[float] = None
    highlight_duration: Optional[float] = None
