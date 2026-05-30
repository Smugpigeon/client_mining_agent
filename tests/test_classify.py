from __future__ import annotations

from leadfinder.domain.enums import LeadType
from leadfinder.domain.models import Lead
from leadfinder.domain.protocols import Stage
from leadfinder.stages.classify import Classifier


def test_classifier_is_a_stage() -> None:
    assert isinstance(Classifier(), Stage)


def test_distributor_is_buyer() -> None:
    lead = Lead(
        company_name="Lagos Beauty Distributors",
        source="bwa",
        business="Cosmetics & Skincare",
        profile="Importer and distributor of skincare.",
    )
    out = Classifier().process(lead)

    assert out is not None
    assert out.is_buyer is True
    assert out.lead_type is LeadType.DISTRIBUTOR
    assert out.skincare_relevant is True


def test_manufacturer_is_seller() -> None:
    lead = Lead(
        company_name="Acme Cosmetics Mfg",
        source="bwa",
        business="Cosmetics",
        profile="Manufacturer of cosmetics.",
    )
    out = Classifier().process(lead)

    assert out is not None
    assert out.is_buyer is False
    assert out.lead_type is LeadType.MANUFACTURER


def test_unknown_local_firm_treated_as_buyer() -> None:
    lead = Lead(company_name="Zaria House Ltd", source="bwa", country="Nigeria")
    out = Classifier().process(lead)

    assert out is not None
    assert out.is_buyer is True
    assert out.lead_type is LeadType.UNKNOWN
