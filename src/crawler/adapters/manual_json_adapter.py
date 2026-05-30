from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import ProductSourceAdapter


class ManualJsonAdapter(ProductSourceAdapter):
    """Load customer-provided product candidates from JSON."""

    source_type = "manual_json"

    def __init__(self, input_path: str | Path, source_label: str = "客户手动 JSON") -> None:
        super().__init__(source_label=source_label)
        self.input_path = Path(input_path)

    def _load_raw_items(self) -> list[dict[str, Any]]:
        if not self.input_path.exists():
            raise FileNotFoundError(f"客户商品 JSON 不存在：{self.input_path}")

        try:
            data = json.loads(self.input_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"客户商品 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

        if isinstance(data, dict) and isinstance(data.get("products"), list):
            data = data["products"]
        if not isinstance(data, list):
            raise ValueError("客户商品 JSON 顶层必须是数组，或包含 products 数组。")

        return [item for item in data if isinstance(item, dict)]

    def load_candidates(self) -> list[dict[str, Any]]:
        return self.normalize_candidates(self._load_raw_items())
