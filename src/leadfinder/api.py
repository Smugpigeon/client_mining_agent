from __future__ import annotations

import json
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

from leadfinder import outreach, pipeline
from leadfinder.domain.models import (
    ChatMessage,
    Lead,
    ProductBlock,
    Recipient,
    SearchParams,
)
from leadfinder.domain.protocols import LeadSource, Stage, Writer
from leadfinder.infra import wx_auth
from leadfinder.infra.email_send import SmtpConfig, SmtpSender, smtp_config_from_env
from leadfinder.infra.http import Fetcher
from leadfinder.infra.llm import LlmClient, llm_config_from_env, parse_assistant_reply
from leadfinder.infra.writers import CsvWriter, ExcelWriter
from leadfinder.sources.beauty_west_africa import BeautyWestAfricaSource
from leadfinder.stages.classify import Classifier
from leadfinder.stages.enrich import EnrichStage
from leadfinder.stages.score import ScoreStage
from leadfinder.stages.verify import VerifyStage

_CACHE_DIR = Path("cache")

_SYSTEM_PROMPT = (
    "你是「客源搜索」小程序里的海外客户开发助手，服务于一家中国护肤品出口商。"
    "任务：帮用户开发海外护肤品**买家**（进口商 / 经销商 / 批发商 / 连锁零售），"
    "重点市场是非洲、中东、南亚。请用简体中文，专业、简洁。\n"
    "规则：\n"
    "1) 当用户让你「找客户 / 找买家 / 找经销商」时，列出真实存在的候选公司，"
    "并在回复**末尾**附一段 JSON，用 <leads></leads> 包裹，数组里每个对象含字段："
    "company_name、country、lead_type(distributor/retailer/manufacturer)、website(若知道)、"
    "business、profile(一句话简介)。不要编造邮箱或电话，不确定的字段留空或省略。\n"
    "2) 普通问题正常对话，不要输出 <leads>。\n"
    "3) 提醒用户：候选公司与联系方式需自行核实，以对方官网 / 平台为准。"
)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str
    leads: list[Lead] = []


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


class CampaignRequest(BaseModel):
    subject: str
    body: str
    recipients: list[Recipient]
    from_name: str = ""
    products: list[ProductBlock] = []
    dry_run: bool = True
    delay: float = 0.8


class CampaignStatus(BaseModel):
    campaign_id: str
    status: str  # pending | running | done | error
    total: int = 0
    sent: int = 0
    failed: int = 0
    error: str | None = None
    results: list[dict[str, Any]] = []


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
    *,
    builder: PipelineBuilder = _default_builder,
    auth: AuthConfig | None = None,
    snapshot: str | None = None,
    smtp: SmtpConfig | None = None,
    llm_client: LlmClient | None = None,
) -> FastAPI:
    app = FastAPI(title="客源搜索 LeadFinder API")
    app_auth = auth or _auth_from_env()
    app_smtp = smtp if smtp is not None else smtp_config_from_env()
    app_llm = llm_client or LlmClient(config=llm_config_from_env())
    snapshot_path = snapshot if snapshot is not None else os.environ.get("LEADFINDER_SNAPSHOT", "")
    jobs: dict[str, JobStatus] = {}
    campaigns: dict[str, CampaignStatus] = {}

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
            if snapshot_path and Path(snapshot_path).exists():
                # Serve a pre-scraped snapshot (cloud demo: instant, no live scraping).
                rows = json.loads(Path(snapshot_path).read_text(encoding="utf-8"))
                job.leads = rows[: request.limit] if request.limit is not None else rows
            else:
                source, stages = builder(request)
                leads = pipeline.run(
                    source=source, stages=stages, params=SearchParams(limit=request.limit)
                )
                job.leads = [lead.model_dump(mode="json") for lead in leads]
            job.count = len(job.leads)
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

    def run_campaign_job(campaign_id: str, request: CampaignRequest) -> None:
        job = campaigns[campaign_id]
        job.status = "running"
        try:
            sender = SmtpSender(config=app_smtp)
            for result in outreach.run_campaign(
                sender=sender,
                recipients=request.recipients,
                subject=request.subject,
                body=request.body,
                from_name=request.from_name,
                products=request.products,
                dry_run=request.dry_run,
                delay=request.delay,
            ):
                job.results.append(result.model_dump())
                if request.dry_run:
                    continue
                if result.ok:
                    job.sent += 1
                else:
                    job.failed += 1
            job.status = "done"
        except Exception as exc:  # report failure to the client, keep the server alive
            job.status = "error"
            job.error = str(exc)

    @app.post("/campaign", response_model=CampaignStatus, dependencies=[Depends(require_auth)])
    def create_campaign(request: CampaignRequest, background: BackgroundTasks) -> CampaignStatus:
        if not request.recipients:
            raise HTTPException(status_code=400, detail="recipients 不能为空")
        if len(request.recipients) > 200:
            raise HTTPException(status_code=400, detail="单次最多 200 个收件人")
        if not request.dry_run and not app_smtp.configured:
            raise HTTPException(status_code=503, detail="SMTP 未配置，无法真实发送")
        campaign_id = uuid.uuid4().hex
        campaigns[campaign_id] = CampaignStatus(
            campaign_id=campaign_id, status="pending", total=len(request.recipients)
        )
        background.add_task(run_campaign_job, campaign_id, request)
        return campaigns[campaign_id]

    @app.get(
        "/campaign/{campaign_id}",
        response_model=CampaignStatus,
        dependencies=[Depends(require_auth)],
    )
    def get_campaign(campaign_id: str) -> CampaignStatus:
        job = campaigns.get(campaign_id)
        if job is None:
            raise HTTPException(status_code=404, detail="campaign not found")
        return job

    @app.post("/chat", response_model=ChatResponse, dependencies=[Depends(require_auth)])
    def chat(request: ChatRequest) -> ChatResponse:
        if not app_llm.configured:
            raise HTTPException(status_code=503, detail="对话未配置（请设置 LLM_API_KEY）")
        messages: list[dict[str, str]] = [{"role": "system", "content": _SYSTEM_PROMPT}]
        messages += [{"role": m.role, "content": m.content} for m in request.messages]
        try:
            raw = app_llm.chat(messages)
        except Exception as exc:  # surface upstream failure, keep the server alive
            raise HTTPException(status_code=502, detail=f"对话失败：{exc}") from exc
        reply, leads = parse_assistant_reply(raw)
        return ChatResponse(reply=reply, leads=leads)

    return app


app = create_app()
