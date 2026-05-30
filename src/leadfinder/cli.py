from __future__ import annotations

import argparse
from pathlib import Path

from leadfinder import pipeline
from leadfinder.domain.models import SearchParams
from leadfinder.domain.protocols import Stage, Writer
from leadfinder.infra.http import Fetcher
from leadfinder.infra.writers import CsvWriter, ExcelWriter, JsonWriter
from leadfinder.sources.beauty_west_africa import BeautyWestAfricaSource
from leadfinder.stages.classify import Classifier
from leadfinder.stages.enrich import EnrichStage
from leadfinder.stages.score import ScoreStage
from leadfinder.stages.verify import VerifyStage

_CACHE_DIR = Path("cache")
_OUTPUT_DIR = Path("data/output")


def main() -> None:
    parser = argparse.ArgumentParser(description="客源搜索 LeadFinder")
    parser.add_argument("--source", default="beauty_west_africa")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--delay", type=float, default=0.5)
    args = parser.parse_args()

    if args.source != "beauty_west_africa":
        parser.error(f"unknown source: {args.source}")

    fetcher = Fetcher(cache_dir=_CACHE_DIR, delay=args.delay)
    source = BeautyWestAfricaSource(fetcher=fetcher)
    stages: list[Stage] = [Classifier(), EnrichStage(fetcher=fetcher), VerifyStage(), ScoreStage()]
    writers: list[Writer] = [
        ExcelWriter(out_dir=_OUTPUT_DIR),
        JsonWriter(out_dir=_OUTPUT_DIR),
        CsvWriter(out_dir=_OUTPUT_DIR),
    ]

    leads = pipeline.run(source=source, stages=stages, params=SearchParams(limit=args.limit))
    paths = [writer.write(leads) for writer in writers]
    fetcher.close()

    high = sum(1 for lead in leads if lead.priority.value == "high")
    with_email = sum(1 for lead in leads if lead.email)
    print(f"leads={len(leads)} with_email={with_email} high_priority={high}")
    for path in paths:
        print(f"  -> {path}")


if __name__ == "__main__":
    main()
