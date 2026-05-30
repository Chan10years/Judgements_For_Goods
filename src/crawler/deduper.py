from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _specs_summary(value: Any) -> str:
    return _clean(value)[:120]


def _normalize_url(value: Any) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url.lower().rstrip("/")
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=(parsed.path or "/").rstrip("/") or "/",
        fragment="",
    )
    return urlunparse(normalized)


def dedupe_products(products: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen_url: dict[str, int] = {}
    seen_weak: dict[tuple[str, str, str], int] = {}
    duplicate_records: list[dict[str, Any]] = []

    for index, product in enumerate(products):
        if not isinstance(product, dict):
            continue
        url_key = _normalize_url(product.get("url"))
        if url_key and url_key in seen_url:
            duplicate_records.append(
                {
                    "removed_index": index,
                    "kept_index": seen_url[url_key],
                    "reason": "duplicate_url",
                    "key": url_key,
                }
            )
            continue

        dimensions_or_specs = _clean(product.get("dimensions")) or _specs_summary(product.get("specs_text"))
        weak_key = (
            _clean(product.get("title")),
            _clean(product.get("price")),
            dimensions_or_specs,
        )
        if not url_key and all(weak_key) and weak_key in seen_weak:
            duplicate_records.append(
                {
                    "removed_index": index,
                    "kept_index": seen_weak[weak_key],
                    "reason": "duplicate_title_price_specs",
                    "key": "|".join(weak_key),
                }
            )
            continue

        deduped_index = len(deduped)
        if url_key:
            seen_url[url_key] = deduped_index
        elif all(weak_key):
            seen_weak[weak_key] = deduped_index
        deduped.append(product)

    report = {
        "before_count": len(products),
        "after_count": len(deduped),
        "removed_count": len(duplicate_records),
        "duplicates": duplicate_records,
    }
    return deduped, report
