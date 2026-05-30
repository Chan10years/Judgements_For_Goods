from __future__ import annotations

from typing import Any

from src.product_loader import normalize_products


EXTRA_CRAWLER_FIELDS = [
    "evidence",
    "evidence_text",
    "manual_review_required",
    "missing_fields",
    "meta_description",
    "h1",
    "parse_success",
    "parse_error",
]


def normalize_crawler_products(parsed_products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized_products = normalize_products(parsed_products)
    output: list[dict[str, Any]] = []
    for index, product in enumerate(normalized_products):
        merged = dict(product)
        source_item = parsed_products[index] if index < len(parsed_products) else {}
        for field in EXTRA_CRAWLER_FIELDS:
            if field in source_item:
                merged[field] = source_item[field]
        if "source" in source_item and source_item.get("source"):
            merged["source"] = source_item["source"]
        output.append(merged)
    return output
