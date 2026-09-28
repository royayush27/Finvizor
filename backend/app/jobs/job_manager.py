"""In-memory async job tracking for the slow portfolio-generation pipeline.

The original app's AI-Optimized flow did ~60 yfinance pulls, trained three
ML models, fit per-symbol ARIMA models, and ran a news-sentiment pass --
all inside a single Streamlit script rerun, which is a large part of why it
felt "frozen" to the user. Here that work runs in a background thread with
real progress reporting; the frontend polls `GET /api/portfolio/jobs/{id}`
instead of staring at a blank page.

This is a single-process, in-memory store -- fine for a portfolio project
and local/single-worker deployment. A multi-worker production deployment
would swap this for Redis or a database-backed queue (e.g. Celery/RQ); the
`JobManager` interface is small enough to re-implement against either
without touching the routes that use it.
"""
from __future__ import annotations

import uuid
from typing import Dict, Optional

from app.models.schemas import JobStatus, PortfolioResult


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobStatus] = {}

    def create_job(self) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobStatus(job_id=job_id, status="pending", progress=0.0)
        return job_id

    def get(self, job_id: str) -> Optional[JobStatus]:
        return self._jobs.get(job_id)

    def mark_running(self, job_id: str, message: Optional[str] = None) -> None:
        self._update(job_id, status="running", message=message)

    def update_progress(self, job_id: str, progress: float, message: Optional[str] = None) -> None:
        self._update(job_id, progress=progress, message=message)

    def mark_completed(self, job_id: str, result: PortfolioResult) -> None:
        self._update(job_id, status="completed", progress=100.0, result=result, message="Done")

    def mark_failed(self, job_id: str, error: str) -> None:
        self._update(job_id, status="failed", error=error, message="Failed")

    def _update(self, job_id: str, **fields) -> None:
        current = self._jobs.get(job_id)
        if current is None:
            return
        self._jobs[job_id] = current.model_copy(update=fields)


job_manager = JobManager()
