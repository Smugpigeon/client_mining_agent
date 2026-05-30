from __future__ import annotations

import csv
import json
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from openpyxl import Workbook

from leadfinder.domain.models import Lead

_COLUMNS = (
    "company_name", "country", "lead_type", "business", "email", "email_status",
    "phone", "website", "size_estimate", "source", "source_url", "score", "priority",
)
_HEADERS = (
    "公司名称", "国家", "客户类型", "主营/品类", "邮箱", "邮箱状态",
    "电话", "网站", "规模估算", "来源", "来源链接", "评分", "优先级",
)


def _path(out_dir: Path, label: str, ext: str) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir / f"{label}_{datetime.now():%Y%m%d_%H%M%S}.{ext}"


class JsonWriter:
    def __init__(self, *, out_dir: Path, label: str = "leads") -> None:
        self._out_dir = out_dir
        self._label = label

    def write(self, leads: Sequence[Lead]) -> Path:
        path = _path(self._out_dir, self._label, "json")
        rows = [lead.model_dump(mode="json") for lead in leads]
        path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        return path


class CsvWriter:
    def __init__(self, *, out_dir: Path, label: str = "leads") -> None:
        self._out_dir = out_dir
        self._label = label

    def write(self, leads: Sequence[Lead]) -> Path:
        path = _path(self._out_dir, self._label, "csv")
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(_COLUMNS), extrasaction="ignore")
            writer.writeheader()
            for lead in leads:
                data = lead.model_dump(mode="json")
                writer.writerow({key: data.get(key, "") for key in _COLUMNS})
        return path


class ExcelWriter:
    def __init__(self, *, out_dir: Path, label: str = "leads") -> None:
        self._out_dir = out_dir
        self._label = label

    def write(self, leads: Sequence[Lead]) -> Path:
        path = _path(self._out_dir, self._label, "xlsx")
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Leads"
        sheet.append(list(_HEADERS))
        for lead in leads:
            data = lead.model_dump(mode="json")
            sheet.append([data.get(key, "") for key in _COLUMNS])
        sheet.freeze_panes = "A2"
        workbook.save(path)
        return path
