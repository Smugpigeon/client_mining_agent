from __future__ import annotations

from collections.abc import Iterator
from itertools import islice

from bs4 import BeautifulSoup

from leadfinder.config import africa_business as cfg
from leadfinder.domain.models import RawRecord, SearchParams
from leadfinder.infra.http import Fetcher


def _country(location: str) -> str | None:
    # "Nairobi, Kenya" -> "Kenya"; "Dubai, United Arab Emirates" -> "United Arab Emirates"
    parts = [p.strip() for p in location.split(",") if p.strip()]
    return parts[-1] if parts else None


class AfricaBusinessSource:
    """LeadSource: africa-business.com cosmetics directory.

    Discovery only — the directory gates contacts (email/phone/website are behind a
    form), so records carry name/country/category/profile; contacts come from enrichment.
    """

    name = cfg.SOURCE_NAME

    def __init__(self, *, fetcher: Fetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, params: SearchParams) -> Iterator[RawRecord]:
        stream = self._stream()
        yield from islice(stream, params.limit) if params.limit is not None else stream

    def _stream(self) -> Iterator[RawRecord]:
        for page in range(cfg.MAX_PAGES):
            offset = page * cfg.PAGE_STEP
            path = cfg.CATEGORY_PATH if offset == 0 else f"{cfg.CATEGORY_PATH}/page/{offset}"
            result = self._fetcher.get(cfg.BASE + path)
            if not result.ok:
                return
            entries = self._parse(result.text)
            if not entries:
                return
            yield from entries

    def _parse(self, html: str) -> list[RawRecord]:
        soup = BeautifulSoup(html, "lxml")
        out: list[RawRecord] = []
        for jl in soup.select(".job-listing"):
            title = jl.select_one(".job-listing-title")
            if title is None:
                continue
            name = title.get_text(" ", strip=True)
            if not name or "Directory" in name:  # skip the directory's own meta-listings
                continue
            anchor = title.find("a", href=True) or jl.find("a", href=True)
            loc = jl.select_one("p.mt-1")
            cat = jl.select_one(".job-listing-company")
            desc = jl.select_one(".job-listing-text")
            out.append(
                RawRecord(
                    source=cfg.SOURCE_NAME,
                    source_url=str(anchor["href"]).split("#")[0] if anchor else None,
                    company_name=name,
                    country=_country(loc.get_text(" ", strip=True)) if loc else None,
                    category=cat.get_text(" ", strip=True) if cat else None,
                    profile=desc.get_text(" ", strip=True) if desc else None,
                )
            )
        return out
