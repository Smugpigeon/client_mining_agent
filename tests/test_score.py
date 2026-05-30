from __future__ import annotations

from leadfinder.domain.enums import LeadType, Priority, Reachability
from leadfinder.domain.models import Lead
from leadfinder.domain.protocols import Stage
from leadfinder.stages.score import ScoreStage


def _score(lead: Lead) -> Lead:
    out = ScoreStage().process(lead)
    assert out is not None
    return out


def test_buyer_with_corporate_email_is_high() -> None:
    out = _score(
        Lead(
            company_name="Lagos Beauty Distributors",
            source="bwa",
            country="Nigeria",
            website="https://x.example",
            email="purchasing@x.example",
            email_status=Reachability.UNKNOWN,
            is_buyer=True,
            skincare_relevant=True,
        )
    )
    assert out.priority is Priority.HIGH
    assert out.score >= 60


def test_seller_is_low() -> None:
    out = _score(
        Lead(
            company_name="Acme Cosmetics Mfg",
            source="bwa",
            country="India",
            lead_type=LeadType.MANUFACTURER,
            skincare_relevant=True,
        )
    )
    assert out.priority is Priority.LOW


def test_buyer_without_email_is_medium() -> None:
    out = _score(
        Lead(
            company_name="Kano Beauty House",
            source="bwa",
            country="Nigeria",
            is_buyer=True,
            skincare_relevant=True,
            website="https://k.example",
        )
    )
    assert out.priority is Priority.MEDIUM


def test_score_stage_is_a_stage() -> None:
    assert isinstance(ScoreStage(), Stage)
