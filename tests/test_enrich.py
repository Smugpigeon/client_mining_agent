from __future__ import annotations

from pathlib import Path

import httpx

from leadfinder.domain.models import Lead
from leadfinder.domain.protocols import Stage
from leadfinder.infra.email_extract import decode_cfemail, filter_emails
from leadfinder.infra.http import Fetcher
from leadfinder.stages.enrich import EnrichStage

_HOME = (
    "<html><body>"
    '<a href="mailto:info@lagosbeauty.example">Email us</a>'
    '<a href="/contact">Contact</a>'
    "</body></html>"
)
_CONTACT = (
    "<html><body>"
    '<a class="__cf_email__" data-cfemail="{token}">[email&#160;protected]</a>'
    "</body></html>"
)


def _cf_token(email: str) -> str:
    key = 0x7A
    parts = [f"{key:02x}"]
    parts += [f"{ord(char) ^ key:02x}" for char in email]
    return "".join(parts)


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if url.endswith("/contact"):
        token = _cf_token("buyer@lagosbeauty.example")
        return httpx.Response(200, text=_CONTACT.format(token=token))
    return httpx.Response(200, text=_HOME)


def _stage(tmp_path: Path) -> EnrichStage:
    fetcher = Fetcher(cache_dir=tmp_path, delay=0.0, transport=httpx.MockTransport(_handler))
    return EnrichStage(fetcher=fetcher)


def test_decode_cfemail_roundtrip() -> None:
    assert decode_cfemail(_cf_token("a@b.com")) == "a@b.com"


def test_filter_drops_sentry_subdomain() -> None:
    junk = "abc123@o4506.ingest.us.sentry.io"
    assert filter_emails({junk, "real@buyer.example"}, "buyer.example") == ["real@buyer.example"]


def test_enrich_finds_corporate_email(tmp_path: Path) -> None:
    lead = Lead(company_name="Lagos Beauty", source="bwa", website="https://lagosbeauty.example")
    out = _stage(tmp_path).process(lead)

    assert out is not None
    assert out.email is not None
    assert out.email.endswith("@lagosbeauty.example")


def test_enrich_skips_when_email_present(tmp_path: Path) -> None:
    lead = Lead(company_name="X", source="bwa", website="https://x.example", email="keep@x.com")
    out = _stage(tmp_path).process(lead)

    assert out is not None
    assert out.email == "keep@x.com"


def test_enrich_skips_social_site(tmp_path: Path) -> None:
    lead = Lead(company_name="X", source="bwa", website="https://facebook.com/x")
    out = _stage(tmp_path).process(lead)

    assert out is not None
    assert out.email is None


def test_enrich_stage_is_a_stage(tmp_path: Path) -> None:
    assert isinstance(_stage(tmp_path), Stage)
