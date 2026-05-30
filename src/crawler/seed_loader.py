from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from src.crawler.models import SeedUrl


REQUIRED_SEED_FIELDS = ["url", "source_name", "category_hint", "note"]


def _normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path or "/"
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        fragment="",
    )
    return urlunparse(normalized)


def _validate_seed_item(item: Any, index: int) -> tuple[SeedUrl | None, dict[str, Any] | None]:
    if not isinstance(item, dict):
        return None, {"index": index, "url": "", "reason": "seed 条目必须是对象。"}

    missing = [field for field in REQUIRED_SEED_FIELDS if field not in item]
    if missing:
        return None, {
            "index": index,
            "url": str(item.get("url", "")),
            "reason": f"缺少字段：{', '.join(missing)}",
        }

    url = str(item.get("url", "")).strip()
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, {"index": index, "url": url, "reason": "URL 必须是 http 或 https 公开地址。"}

    seed = SeedUrl(
        url=_normalize_url(url),
        source_name=str(item.get("source_name", "")).strip(),
        category_hint=str(item.get("category_hint", "")).strip(),
        note=str(item.get("note", "")).strip(),
    )
    if not seed.source_name:
        return None, {"index": index, "url": url, "reason": "source_name 不能为空。"}
    return seed, None


def load_seed_urls(seed_path: str | Path) -> tuple[list[SeedUrl], list[dict[str, Any]]]:
    path = Path(seed_path)
    if not path.exists():
        raise FileNotFoundError(f"seed URL 文件不存在：{path}")

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"seed URL JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

    if not isinstance(data, list):
        raise ValueError("seed URL JSON 顶层必须是数组。")

    seeds: list[SeedUrl] = []
    invalid_entries: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for index, item in enumerate(data, start=1):
        seed, invalid = _validate_seed_item(item, index)
        if invalid is not None:
            invalid_entries.append(invalid)
            continue
        assert seed is not None
        if seed.url in seen_urls:
            invalid_entries.append({"index": index, "url": seed.url, "reason": "重复 URL，已跳过。"})
            continue
        seen_urls.add(seed.url)
        seeds.append(seed)

    return seeds, invalid_entries
