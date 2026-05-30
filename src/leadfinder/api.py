from __future__ import annotations

import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

from leadfinder import pipeline
from leadfinder.domain.models import SearchParams
from leadfinder.domain.protocols import LeadSource, Stage
from leadfinder.infra.http import Fetcher
from leadfinder.sources.beauty_west_africa import BeautyWestAfricaSource
from leadfinder.stages.classify import Classifier
from leadfinder.stages.enrich import EnrichStage
from leadfinder.stages.score import ScoreStage
from leadfinder.stages.verify import VerifyStage

_CACHE_DIR = Path("cache")


class SearchRequest(BaseModel):
    source: str = "beauty_west_africa"
    limit: int | None = None
    delay: float = 0.3


class JobStatus(BaseModel):
    job_id: str
    status: str  # pending | running | done | error
    count: int = 0
    error: str | None = None
    leads: list[dict[str, Any]] = []


PipelineBuilder = Callable[[SearchRequest], tuple[LeadSource, list[Stage]]]


def _default_builder(request: SearchRequest) -> tuple[LeadSource, list[Stage]]:
    fetcher = Fetcher(cache_dir=_CACHE_DIR, delay=request.delay)
    source = BeautyWestAfricaSource(fetcher=fetcher)
    stages: list[Stage] = [Classifier(), EnrichStage(fetcher=fetcher), VerifyStage(), ScoreStage()]
    return source, stages


def create_app(*, builder: PipelineBuilder = _default_builder) -> FastAPI:
    app = FastAPI(title="客源搜索 LeadFinder API")
    jobs: dict[str, JobStatus] = {}

    def run_job(job_id: str, request: SearchRequest) -> None:
        job = jobs[job_id]
        job.status = "running"
        try:
            source, stages = builder(request)
            leads = pipeline.run(
                source=source, stages=stages, params=SearchParams(limit=request.limit)
            )
            job.leads = [lead.model_dump(mode="json") for lead in leads]
            job.count = len(leads)
            job.status = "done"
        except Exception as exc:  # report failure to the client, keep the server alive
            job.status = "error"
            job.error = str(exc)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs", response_model=JobStatus)
    def create_job(request: SearchRequest, background: BackgroundTasks) -> JobStatus:
        if request.source != "beauty_west_africa":
            raise HTTPException(status_code=400, detail=f"unknown source: {request.source}")
        job_id = uuid.uuid4().hex
        jobs[job_id] = JobStatus(job_id=job_id, status="pending")
        background.add_task(run_job, job_id, request)
        return jobs[job_id]

    @app.get("/jobs/{job_id}", response_model=JobStatus)
    def get_job(job_id: str) -> JobStatus:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    return app


app = create_app()
