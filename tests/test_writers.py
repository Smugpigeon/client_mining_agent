from __future__ import annotations

import json
from pathlib import Path

from leadfinder.domain.enums import Priority
from leadfinder.domain.models import Lead
from leadfinder.domain.protocols import Writer
from leadfinder.infra.writers import CsvWriter, ExcelWriter, JsonWriter


def _leads() -> list[Lead]:
    return [Lead(company_name="Lagos Beauty", source="bwa", email="a@lagos.example",
                 priority=Priority.HIGH, score=80)]


def test_all_writers_create_nonempty_files(tmp_path: Path) -> None:
    writers: list[Writer] = [
        JsonWriter(out_dir=tmp_path),
        CsvWriter(out_dir=tmp_path),
        ExcelWriter(out_dir=tmp_path),
    ]
    for writer in writers:
        path = writer.write(_leads())
        assert path.exists()
        assert path.stat().st_size > 0


def test_json_writer_content(tmp_path: Path) -> None:
    path = JsonWriter(out_dir=tmp_path).write(_leads())
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data[0]["company_name"] == "Lagos Beauty"
    assert data[0]["priority"] == "high"
