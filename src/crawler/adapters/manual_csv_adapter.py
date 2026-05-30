from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import ProductSourceAdapter


class ManualCsvAdapter(ProductSourceAdapter):
    """Load customer-provided product candidates from CSV."""

    source_type = "manual_csv"

    def __init__(self, input_path: str | Path, source_label: str = "客户手动 CSV", encoding: str = "utf-8-sig") -> None:
        super().__init__(source_label=source_label)
        self.input_path = Path(input_path)
        self.encoding = encoding

    def _load_raw_items(self) -> list[dict[str, Any]]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"客户商品 CSV 不存在：{self.input_path}")

        with self.input_path.open("r", encoding=self.encoding, newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            if not reader.fieldnames:
                raise ValueError("客户商品 CSV 必须包含表头。")
            return [{key: value for key, value in row.items() if key is not None} for row in reader]

    def load_candidates(self) -> list[dict[str, Any]]:
        return self.normalize_candidates(self._load_raw_items())
