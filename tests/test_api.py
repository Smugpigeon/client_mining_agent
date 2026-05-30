from __future__ import annotations

from collections.abc import Iterator

from fastapi.testclient import TestClient

from leadfinder.api import SearchRequest, create_app
from leadfinder.domain.models import RawRecord, SearchParams
from leadfinder.domain.protocols import LeadSource, Stage
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
