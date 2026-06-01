from __future__ import annotations

from pathlib import Path

import httpx

from leadfinder.domain.models import SearchParams
from leadfinder.domain.protocols import LeadSource
from leadfinder.infra.http import Fetcher
from leadfinder.sources.africa_business import AfricaBusinessSource

_PAGE1 = """
<div class="job-listing">
  <h3 class="job-listing-title"><a href="/b/Suzie#contact">Suzie Beauty Ltd.</a></h3>
  <p class="mt-1">Nairobi, Kenya</p>
  <h4 class="job-listing-company">Perfumes &amp; Cosmetics</h4>
  <div class="job-listing-text">Suzie Beauty cosmetics for African skin.</div>
</div>
<div class="job-listing">
  <h3 class="job-listing-title"><a href="/b/MAK4">MAK4 Limited</a></h3>
  <p class="mt-1">Kampala, Uganda</p>
  <h4 class="job-listing-company">Perfumes &amp; Cosmetics</h4>
  <div class="job-listing-text">Importer and distributor of cosmetics.</div>
</div>
<div class="job-listing">
  <h3 class="job-listing-title"><a href="/b/dir">X Importers Directory</a></h3>
  <p class="mt-1">Africa, Kenya</p>
  <h4 class="job-listing-company">Perfumes &amp; Cosmetics</h4>
</div>
"""


def _handler(request: httpx.Request) -> httpx.Response:
    if "/page/" in str(request.url):
        return httpx.Response(200, text="<html><body>no listings</body></html>")
    return httpx.Response(200, text=f"<html><body>{_PAGE1}</body></html>")


def _source(tmp_path: Path) -> AfricaBusinessSource:
    fetcher = Fetcher(cache_dir=tmp_path, delay=0.0, transport=httpx.MockTransport(_handler))
    return AfricaBusinessSource(fetcher=fetcher)


def test_is_a_lead_source(tmp_path: Path) -> None:
    assert isinstance(_source(tmp_path), LeadSource)


def test_parses_companies_and_skips_meta_directory(tmp_path: Path) -> None:
    records = list(_source(tmp_path).fetch(SearchParams()))

    assert len(records) == 2  # the "...Importers Directory" meta-entry is skipped
    first = records[0]
    assert first.company_name == "Suzie Beauty Ltd."
    assert first.country == "Kenya"
    assert first.category == "Perfumes & Cosmetics"
    assert first.source == "Africa Business Directory"
    assert first.source_url is not None and "#contact" not in first.source_url


def test_limit_caps_results(tmp_path: Path) -> None:
    assert len(list(_source(tmp_path).fetch(SearchParams(limit=1)))) == 1
