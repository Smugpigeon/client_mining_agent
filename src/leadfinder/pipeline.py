from __future__ import annotations

from collections.abc import Iterable, Sequence

from leadfinder.domain.models import Lead, RawRecord, SearchParams
from leadfinder.domain.protocols import LeadSource, Stage
from leadfinder.infra.http import canonical_url


def _size(tier: str) -> str | None:
    tier = tier.lower()
    if tier == "gold":
        return "较大(Gold)"
    if tier == "silver":
        return "中(Silver)"
    return None


def _to_lead(record: RawRecord) -> Lead:
    return Lead(
        company_name=record.company_name,
        country=record.country,
        website=record.website,
        business=record.category,
        profile=record.profile,
        source=record.source,
        source_url=record.source_url,
        size_estimate=_size(record.extra.get("tier", "")),
    )


def _dedupe_key(lead: Lead) -> str:
    if lead.website:
        return "web:" + canonical_url(lead.website)
    return "name:" + lead.company_name.strip().lower()


def _dedupe(leads: Iterable[Lead]) -> list[Lead]:
    best: dict[str, Lead] = {}
    for lead in leads:
        best.setdefault(_dedupe_key(lead), lead)
    return list(best.values())


def run(*, source: LeadSource, stages: Sequence[Stage], params: SearchParams) -> list[Lead]:
    """Discover → dedupe (before the expensive stage chain) → run stages → sort by score."""
    leads = _dedupe(_to_lead(record) for record in source.fetch(params))
    processed: list[Lead] = []
    for lead in leads:
        current = lead
        dropped = False
        for stage in stages:
            result = stage.process(current)
            if result is None:
                dropped = True
                break
            current = result
        if not dropped:
            processed.append(current)
    processed.sort(key=lambda lead: lead.score, reverse=True)
    return processed
