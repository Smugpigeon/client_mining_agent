from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from leadfinder.api import AuthConfig, SearchRequest, create_app
from leadfinder.domain.models import RawRecord, SearchParams
from leadfinder.domain.protocols import LeadSource, Stage
from leadfinder.infra.email_send import SmtpConfig
from leadfinder.infra.llm import LlmClient, LlmConfig
from leadfinder.stages.classify import Classifier
from leadfinder.stages.score import ScoreStage


class _FakeSource:
    name = "fake"

    def fetch(self, params: SearchParams) -> Iterator[RawRecord]:
        yield RawRecord(
            source="fake",
            company_name="Lagos Beauty Distributors",
            country="Nigeria",
            category="Cosmetics & Skincare",
            profile="Importer and distributor of skincare.",
        )


def _fake_builder(request: SearchRequest) -> tuple[LeadSource, list[Stage]]:
    stages: list[Stage] = [Classifier(), ScoreStage()]
    return _FakeSource(), stages


def test_health() -> None:
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_unknown_source_is_400() -> None:
    client = TestClient(create_app())
    assert client.post("/jobs", json={"source": "nope"}).status_code == 400


def test_unknown_job_is_404() -> None:
    client = TestClient(create_app())
    assert client.get("/jobs/does-not-exist").status_code == 404


def test_job_runs_to_done_with_fake_builder() -> None:
    client = TestClient(create_app(builder=_fake_builder))
    created = client.post("/jobs", json={"source": "beauty_west_africa", "limit": 1})
    assert created.status_code == 200
    job_id = created.json()["job_id"]

    status = client.get(f"/jobs/{job_id}").json()
    assert status["status"] == "done"
    assert status["count"] == 1
    assert status["leads"][0]["company_name"] == "Lagos Beauty Distributors"


def test_export_done_job_returns_csv() -> None:
    client = TestClient(create_app(builder=_fake_builder))
    created = client.post("/jobs", json={"source": "beauty_west_africa", "limit": 1})
    job_id = created.json()["job_id"]
    assert client.get(f"/jobs/{job_id}").json()["status"] == "done"

    response = client.get(f"/jobs/{job_id}/export", params={"fmt": "csv"})
    assert response.status_code == 200
    assert "Lagos Beauty Distributors" in response.text


def test_export_unknown_job_is_404() -> None:
    client = TestClient(create_app())
    assert client.get("/jobs/nope/export").status_code == 404


def test_login_with_fake_wx() -> None:
    def fake_get(url: str, params: dict[str, str]) -> dict[str, Any]:
        return {"openid": "u-1", "session_key": "k"}

    auth = AuthConfig(appid="a", secret="b", session_secret="s", http_get=fake_get)
    client = TestClient(create_app(auth=auth))
    response = client.post("/auth/login", json={"code": "xyz"})

    assert response.status_code == 200
    assert response.json()["openid"] == "u-1"
    assert response.json()["token"]


def test_login_not_configured_is_503() -> None:
    client = TestClient(create_app(auth=AuthConfig()))
    assert client.post("/auth/login", json={"code": "x"}).status_code == 503


def test_campaign_dry_run_previews() -> None:
    client = TestClient(create_app())
    payload = {
        "subject": "你好 {{company_name}}",
        "body": "我们是护肤品出口商，想与{{company_name}}合作。",
        "recipients": [{"email": "a@b.com", "company_name": "Acme"}],
        "dry_run": True,
    }
    created = client.post("/campaign", json=payload)
    assert created.status_code == 200
    cid = created.json()["campaign_id"]

    status = client.get(f"/campaign/{cid}").json()
    assert status["status"] == "done"
    assert "Acme" in status["results"][0]["preview"]


def test_campaign_real_send_without_smtp_is_503() -> None:
    client = TestClient(create_app(smtp=SmtpConfig()))
    payload = {"subject": "s", "body": "b", "recipients": [{"email": "a@b.com"}], "dry_run": False}
    assert client.post("/campaign", json=payload).status_code == 503


def test_snapshot_mode_serves_bundled_leads(tmp_path: Path) -> None:
    snap = tmp_path / "leads.json"
    snap.write_text(
        json.dumps([{"company_name": "Snap Co", "source": "bwa", "priority": "high"}]),
        encoding="utf-8",
    )
    client = TestClient(create_app(snapshot=str(snap)))
    created = client.post("/jobs", json={"source": "beauty_west_africa"})
    status = client.get(f"/jobs/{created.json()['job_id']}").json()

    assert status["status"] == "done"
    assert status["count"] == 1
    assert status["leads"][0]["company_name"] == "Snap Co"


def _fake_chat(config: LlmConfig, messages: list[dict[str, str]]) -> str:
    return (
        "为你找到几家尼日利亚的护肤品进口商：\n"
        '<leads>[{"company_name":"Lagos Beauty Imports","country":"Nigeria",'
        '"lead_type":"distributor","website":"lagosbeauty.example"}]</leads>'
    )


def test_chat_returns_reply_and_parsed_leads() -> None:
    client = TestClient(
        create_app(llm_client=LlmClient(config=LlmConfig(api_key="x"), chat_fn=_fake_chat))
    )
    resp = client.post(
        "/chat", json={"messages": [{"role": "user", "content": "找尼日利亚进口商"}]}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "尼日利亚" in body["reply"]
    assert "<leads>" not in body["reply"]  # JSON block stripped from prose
    assert body["leads"][0]["company_name"] == "Lagos Beauty Imports"
    assert body["leads"][0]["source"] == "chat"


def test_chat_not_configured_is_503() -> None:
    client = TestClient(create_app(llm_client=LlmClient(config=LlmConfig())))
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    assert client.post("/chat", json=payload).status_code == 503
