from __future__ import annotations

from leadfinder.domain.enums import Reachability
from leadfinder.domain.models import Lead
from leadfinder.domain.protocols import EmailVerifier, Stage
from leadfinder.infra.email_verify import EmailChecker
from leadfinder.stages.verify import VerifyStage


def _checker(mx: bool = True) -> EmailChecker:
    return EmailChecker(mx_lookup=lambda _domain: mx)


def test_checker_is_an_email_verifier() -> None:
    assert isinstance(_checker(), EmailVerifier)


def test_corporate_email_unknown_with_mx() -> None:
    result = _checker(mx=True).verify("hello@acme-distribution.com")
    assert result.reachability is Reachability.UNKNOWN
    assert result.has_mx is True
    assert result.is_free is False


def test_no_mx_is_invalid() -> None:
    assert _checker(mx=False).verify("x@acme-distribution.com").reachability is Reachability.INVALID


def test_disposable_is_risky() -> None:
    result = _checker(mx=True).verify("x@mailinator.com")
    assert result.reachability is Reachability.RISKY
    assert result.is_disposable is True


def test_buyer_role_detected() -> None:
    result = _checker().verify("purchasing@acme-distribution.com")
    assert result.role_kind == "buyer"
    assert result.is_role is True


def test_free_domain_flagged() -> None:
    assert _checker().verify("john@gmail.com").is_free is True


def test_bad_syntax_invalid() -> None:
    assert _checker().verify("not-an-email").reachability is Reachability.INVALID


def test_verify_stage_nudges_buyer() -> None:
    stage = VerifyStage(verifier=_checker(mx=True))
    lead = Lead(company_name="X", source="bwa", email="procurement@x-importers.com", is_buyer=False)
    out = stage.process(lead)

    assert out is not None
    assert out.email_status is Reachability.UNKNOWN
    assert out.is_buyer is True


def test_verify_stage_is_a_stage() -> None:
    assert isinstance(VerifyStage(), Stage)
