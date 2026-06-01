from __future__ import annotations

from collections.abc import Callable

from leadfinder.domain.protocols import LeadSource
from leadfinder.sources.africa_business import AfricaBusinessSource
from leadfinder.sources.beauty_west_africa import BeautyWestAfricaSource

# name -> source class (each constructed with a keyword `fetcher`).
SOURCES: dict[str, Callable[..., LeadSource]] = {
    "beauty_west_africa": BeautyWestAfricaSource,
    "africa_business": AfricaBusinessSource,
}
