from __future__ import annotations

from leadfinder.domain.enums import Priority, Reachability
from leadfinder.domain.models import SCHEMA_VERSION, Lead, RawRecord


def test_lead_minimal_construction() -> None:
    lead = Lead(company_name="Acme Distributors", source="beauty_west_africa")
    assert lead.priority is Priority.LOW
    assert lead.email_status is Reachability.UNKNOWN
    assert lead.is_buyer is False
    assert lead.schema_version == SCHEMA_VERSION


def test_rawrecord_requires_name_and_source() -> None:
    rec = RawRecord(source="bwa", company_name="X Cosmetics")
    assert rec.company_name == "X Cosmetics"
    assert rec.extra == {}
