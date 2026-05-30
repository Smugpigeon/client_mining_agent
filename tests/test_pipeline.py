from __future__ import annotations

from collections.abc import Iterator

from leadfinder import pipeline
from leadfinder.domain.models import RawRecord, SearchParams
from leadfinder.stages.classify import Classifier
from leadfinder.stages.score import ScoreStage


class _FakeSource:
    name = "fake"

    def __init__(self, records: list[RawRecord]) -> None:
        self._records = records

    def fetch(self, params: SearchParams) -> Iterator[RawRecord]:
        yield from self._records


def test_pipeline_dedupes_and_sorts_buyer_first() -> None:
    records = [
        RawRecord(
            source="fake",
            company_name="Lagos Beauty Distributors",
            country="Nigeria",
            website="https://lagos.example",
            category="Cosmetics & Skincare",
            profile="Importer and distributor of skincare.",
        ),
        RawRecord(
            source="fake",
            company_name="Lagos Beauty Distributors",
            country="Nigeria",
            website="https://lagos.example/?utm_source=ad",  # same canonical URL → duplicate
            category="Cosmetics & Skincare",
        ),
        RawRecord(
            source="fake",
            company_name="Acme Cosmetics Mfg",
            country="India",
            category="Cosmetics",
            profile="Manufacturer of cosmetics.",
        ),
    ]

    leads = pipeline.run(
        source=_FakeSource(records),
        stages=[Classifier(), ScoreStage()],
        params=SearchParams(),
    )

    assert len(leads) == 2  # the two Lagos rows collapsed into one
    assert leads[0].company_name == "Lagos Beauty Distributors"  # buyer outranks seller
    assert leads[0].score > leads[-1].score
