from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import ProductSourceAdapter
from src.crawler.models import resolve_project_path
from src.crawler.pipeline import run_crawler


class StaticPageAdapter(ProductSourceAdapter):
    """Reuse the Stage 8 public URL crawler pipeline as a product source adapter."""

    source_type = "static_page"

    def __init__(
        self,
        config_path: str | Path = "config/crawler_config.json",
        seed_path: str | Path = "data/seed_urls.json",
        source_label: str = "公开 URL 页面",
    ) -> None:
        super().__init__(source_label=source_label)
        self.config_path = Path(config_path)
        self.seed_path = Path(seed_path)

    def _load_pipeline_products(self, report: dict[str, Any]) -> list[dict[str, Any]]:
        product_path_text = report.get("output_paths", {}).get("products", "outputs/crawler_products.json")
        product_path = resolve_project_path(product_path_text)
        if not product_path.exists():
            return []

        try:
            data = json.loads(product_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"公开页面商品输出 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

        if isinstance(data, dict) and isinstance(data.get("products"), list):
            data = data["products"]
        if not isinstance(data, list):
            raise ValueError("公开页面商品输出必须是数组，或包含 products 数组。")
        return [item for item in data if isinstance(item, dict)]

    def load_candidates(self) -> list[dict[str, Any]]:
        report = run_crawler(config_path=self.config_path, seed_path=self.seed_path)
        return self.normalize_candidates(self._load_pipeline_products(report))
