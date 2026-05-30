from __future__ import annotations

import os
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from leadfinder import pipeline
from leadfinder.domain.models import Lead, SearchParams
from leadfinder.domain.protocols import LeadSource, Stage, Writer
from leadfinder.infra import wx_auth
from leadfinder.infra.http import Fetcher
from leadfinder.infra.writers import CsvWriter, ExcelWriter
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


class LoginRequest(BaseModel):
    code: str


class LoginResponse(BaseModel):
    token: str
    openid: str


PipelineBuilder = Callable[[SearchRequest], tuple[LeadSource, list[Stage]]]


def _default_builder(request: SearchRequest) -> tuple[LeadSource, list[Stage]]:
    fetcher = Fetcher(cache_dir=_CACHE_DIR, delay=request.delay)
    source = BeautyWestAfricaSource(fetcher=fetcher)
    stages: list[Stage] = [Classifier(), EnrichStage(fetcher=fetcher), VerifyStage(), ScoreStage()]
    return source, stages


@dataclass
class AuthConfig:
    appid: str = ""
    secret: str = ""
    session_secret: str = ""
    required: bool = False
    http_get: wx_auth.HttpGet | None = None

    @property
    def configured(self) -> bool:
        return bool(self.appid and self.secret and self.session_secret)


def _auth_from_env() -> AuthConfig:
    return AuthConfig(
        appid=os.environ.get("WX_APPID", ""),
        secret=os.environ.get("WX_SECRET", ""),
        session_secret=os.environ.get("WX_SESSION_SECRET", ""),
        required=os.environ.get("AUTH_REQUIRED", "") not in ("", "0", "false", "False"),
    )


def create_app(
    *, builder: PipelineBuilder = _default_builder, auth: AuthConfig | None = None
) -> FastAPI:
    app = FastAPI(title="客源搜索 LeadFinder API")
    app_auth = auth or _auth_from_env()
    jobs: dict[str, JobStatus] = {}

    def require_auth(authorization: str | None = Header(default=None)) -> None:
        if not app_auth.required:
            return
        token = (authorization or "").removeprefix("Bearer ").strip()
        if wx_auth.verify_token(token, secret=app_auth.session_secret) is None:
            raise HTTPException(status_code=401, detail="invalid or missing token")

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

    @app.post("/auth/login", response_model=LoginResponse)
    def login(request: LoginRequest) -> LoginResponse:
        if not app_auth.configured:
            raise HTTPException(status_code=503, detail="wx auth not configured")
        try:
            openid = wx_auth.code_to_openid(
                request.code,
                appid=app_auth.appid,
                secret=app_auth.secret,
                http_get=app_auth.http_get or wx_auth.default_http_get,
            )
        except wx_auth.WxAuthError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        token = wx_auth.issue_token(openid, secret=app_auth.session_secret)
        return LoginResponse(token=token, openid=openid)

    @app.post("/jobs", response_model=JobStatus, dependencies=[Depends(require_auth)])
    def create_job(request: SearchRequest, background: BackgroundTasks) -> JobStatus:
        if request.source != "beauty_west_africa":
            raise HTTPException(status_code=400, detail=f"unknown source: {request.source}")
        job_id = uuid.uuid4().hex
        jobs[job_id] = JobStatus(job_id=job_id, status="pending")
        background.add_task(run_job, job_id, request)
        return jobs[job_id]

    @app.get("/jobs/{job_id}", response_model=JobStatus, dependencies=[Depends(require_auth)])
    def get_job(job_id: str) -> JobStatus:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return job

    @app.get("/jobs/{job_id}/export", dependencies=[Depends(require_auth)])
    def export_job(job_id: str, fmt: str = "xlsx") -> FileResponse:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if job.status != "done":
            raise HTTPException(status_code=409, detail=f"job not done: {job.status}")
        if fmt not in ("xlsx", "csv"):
            raise HTTPException(status_code=400, detail=f"unknown format: {fmt}")
        leads = [Lead.model_validate(row) for row in job.leads]
        out_dir = Path(tempfile.mkdtemp(prefix="leadfinder_export_"))
        label = f"leads_{job_id[:8]}"
        if fmt == "xlsx":
            writer: Writer = ExcelWriter(out_dir=out_dir, label=label)
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            writer = CsvWriter(out_dir=out_dir, label=label)
            media = "text/csv"
        path = writer.write(leads)
        return FileResponse(path, media_type=media, filename=path.name)

    return app


app = create_app()
