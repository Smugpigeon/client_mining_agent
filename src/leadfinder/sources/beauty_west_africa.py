from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from typing import Any

from bs4 import BeautifulSoup

from leadfinder.config import bwa
from leadfinder.domain.models import RawRecord, SearchParams
from leadfinder.infra.http import Fetcher

_LABELS = (bwa.LABEL_WEBSITE, bwa.LABEL_COUNTRY, bwa.LABEL_CATEGORY)
_LABEL_SPLIT = "|".join(re.escape(label) for label in _LABELS)


class BeautyWestAfricaSource:
    """LeadSource for the Beauty West Africa exhibitor directory (JSON list API + detail pages)."""

    name = bwa.SOURCE_NAME

    def __init__(self, *, fetcher: Fetcher) -> None:
        self._fetcher = fetcher

    def fetch(self, params: SearchParams) -> Iterator[RawRecord]:
        for index, entry in enumerate(self._list_entries()):
            if params.limit is not None and index >= params.limit:
                return
            yield self._to_record(entry)

    def _list_entries(self) -> Iterator[dict[str, Any]]:
        first = self._list_page(1)
        if first is None:
            return
        total = int(first.get("TotalRecords", 0)) or len(first.get("ListData", []))
        pages = max(1, math.ceil(total / bwa.PAGE_SIZE))
        seen: set[str] = set()
        for page in range(1, pages + 1):
            data = first if page == 1 else self._list_page(page)
            if data is None:
                continue
            for entry in data.get("ListData", []):
                eid = entry.get("ExhibitorId")
                if eid and eid not in seen:
                    seen.add(eid)
                    yield entry

    def _list_page(self, page_index: int) -> dict[str, Any] | None:
        url = (
            f"{bwa.LIST_HANDLER}?pageIndex={page_index}"
            f"&pageSize={bwa.PAGE_SIZE}&q={bwa.LIST_QUERY_ALL}"
        )
        result = self._fetcher.get(url)
        if not result.ok:
            return None
        try:
            parsed = json.loads(result.text)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _to_record(self, entry: dict[str, Any]) -> RawRecord:
        eid = str(entry.get("ExhibitorId", ""))
        detail = self._detail(eid)
        return RawRecord(
            source=bwa.SOURCE_NAME,
            source_url=bwa.DETAIL_URL.format(exhibitor_id=eid),
            company_name=detail.get("name") or str(entry.get("CompanyName", "")).strip(),
            country=detail.get("country") or entry.get("Country") or None,
            website=detail.get("website"),
            category=detail.get("category"),
            profile=detail.get("profile"),
            extra={
                "tier": str(entry.get("ExhibitorTier", "")),
                "stand": str(entry.get("StandNo", "")),
            },
        )

    def _detail(self, exhibitor_id: str) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        if not exhibitor_id:
            return out
        result = self._fetcher.get(bwa.DETAIL_URL.format(exhibitor_id=exhibitor_id))
        if not result.ok:
            return out
        soup = BeautifulSoup(result.text, "lxml")
        name = soup.find(id=bwa.NAME_ID)
        if name is not None:
            out["name"] = name.get_text(" ", strip=True)
        profile = soup.find(id=bwa.PROFILE_ID)
        if profile is not None:
            out["profile"] = profile.get_text(" ", strip=True)
        out["website"] = _link_after(soup, bwa.LABEL_WEBSITE)
        out["country"] = _value_after(soup, bwa.LABEL_COUNTRY)
        out["category"] = _value_after(soup, bwa.LABEL_CATEGORY)
        return out


def _value_after(soup: Any, label: str) -> str | None:
    node = soup.find(string=lambda s: bool(s) and label in s)
    if node is None:
        return None
    box = node.find_parent(["span", "p", "div"])
    text = box.get_text(" ", strip=True) if box else str(node)
    value = re.split(_LABEL_SPLIT, text.split(label, 1)[-1])[0]
    return value.strip(" : ") or None


def _link_after(soup: Any, label: str) -> str | None:
    node = soup.find(string=lambda s: bool(s) and label in s)
    if node is None:
        return None
    box = node.find_parent(["span", "p", "div"])
    anchor = box.find("a", href=True) if box else None
    if anchor is None:
        return None
    href = str(anchor["href"]).strip()
    if href.lower().startswith(("http://", "https://")) and "beautywestafrica" not in href.lower():
        return href
    return None
