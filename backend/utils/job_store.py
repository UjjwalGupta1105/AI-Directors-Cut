import json
import os
from typing import Dict, Optional
from models import JobState


_jobs: Dict[str, JobState] = {}
# Use the project-root temp/ directory, computed via file_manager
_store_path = os.path.join(os.path.dirname(__file__), "..", "..", "temp", "jobs.json")


def _persist():
    os.makedirs(os.path.dirname(_store_path), exist_ok=True)
    with open(_store_path, "w") as f:
        json.dump({k: v.model_dump() for k, v in _jobs.items()}, f, indent=2)


def _load():
    """Load jobs from disk on server startup so restarts don't lose job state."""
    global _jobs
    try:
        if os.path.exists(_store_path):
            with open(_store_path, "r") as f:
                data = json.load(f)
            _jobs = {k: JobState(**v) for k, v in data.items()}
    except Exception:
        _jobs = {}


# Load on import (server startup)
_load()


def create_job(job: JobState):
    _jobs[job.job_id] = job
    _persist()


def get_job(job_id: str) -> Optional[JobState]:
    return _jobs.get(job_id)


def update_job(job_id: str, **kwargs):
    job = _jobs.get(job_id)
    if not job:
        return
    for k, v in kwargs.items():
        setattr(job, k, v)
    _persist()
