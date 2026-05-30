from __future__ import annotations

import json
from pathlib import Path

import httpx

from leadfinder.config import bwa
from leadfinder.domain.models import SearchParams
from leadfinder.infra.http import Fetcher
from leadfinder.sources.beauty_west_africa import BeautyWestAfricaSource

_LIST_JSON = json.dumps(
    {
        "TotalRecords": 2,
        "ListData": [
            {
                "ExhibitorId": "e1",
                "CompanyName": "Lagos Beauty Distributors",
                "Country": "Nigeria",
                "ExhibitorTier": "Gold",
                "StandNo": "1A1",
            },
            {
                "ExhibitorId": "e2",
                "CompanyName": "Acme Cosmetics Mfg",
                "Country": "India",
                "ExhibitorTier": "Standard",
                "StandNo": "2B2",
            },
        ],
    }
)

_DETAIL_E1 = (
    '<html><body>'
    '<span id="cphContents_lblCompanyNamehead">Lagos Beauty Distributors</span>'
    '<span id="cphContents_lblOnlineProfile">Importer &amp; distributor of skincare.</span>'
    "<p><span><strong>Website: </strong>"
    "<a href='https://lagos.example'>Click Here</a></span></p>"
    "<p><span><strong>Country: </strong>Nigeria</span></p>"
    "<p><span><strong>Product Category: </strong>Cosmetics &amp; Skincare</span></p>"
    '</body></html>'
)

_DETAIL_E2 = (
    '<html><body>'
    '<span id="cphContents_lblCompanyNamehead">Acme Cosmetics Mfg</span>'
    '<span id="cphContents_lblOnlineProfile">Manufacturer of cosmetics.</span>'
    "<p><span><strong>Country: </strong>India</span></p>"
    '</body></html>'
)


def _handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "ExhibitorListHandler" in url:
        return httpx.Response(200, text=_LIST_JSON)
    if "ExhiId=e1" in url:
        return httpx.Response(200, text=_DETAIL_E1)
    if "ExhiId=e2" in url:
        return httpx.Response(200, text=_DETAIL_E2)
    return httpx.Response(404)


def _source(tmp_path: Path) -> BeautyWestAfricaSource:
    fetcher = Fetcher(cache_dir=tmp_path, delay=0.0, transport=httpx.MockTransport(_handler))
    return BeautyWestAfricaSource(fetcher=fetcher)


def test_fetch_yields_parsed_records(tmp_path: Path) -> None:
    records = list(_source(tmp_path).fetch(SearchParams()))

    assert len(records) == 2
    first = records[0]
    assert first.company_name == "Lagos Beauty Distributors"
    assert first.country == "Nigeria"
    assert first.website == "https://lagos.example"
    assert first.category == "Cosmetics & Skincare"
    assert first.source == bwa.SOURCE_NAME
    assert first.extra["tier"] == "Gold"


def test_fetch_respects_limit(tmp_path: Path) -> None:
    records = list(_source(tmp_path).fetch(SearchParams(limit=1)))

    assert len(records) == 1
    assert records[0].company_name == "Lagos Beauty Distributors"
