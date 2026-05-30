from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from src.product_loader import PRODUCT_FIELDS, normalize_products


FIELD_ALIASES = {
    "id": "product_id",
    "sku": "product_id",
    "name": "title",
    "商品名称": "title",
    "标题": "title",
    "名称": "title",
    "品牌": "brand",
    "类目": "category",
    "分类": "category",
    "价格": "price",
    "店铺": "shop",
    "供应商": "shop",
    "材质": "material",
    "颜色": "color",
    "尺寸": "dimensions",
    "规格尺寸": "dimensions",
    "size": "dimensions",
    "风格": "style",
    "平台": "platform",
    "来源": "source",
    "source_name": "source",
    "链接": "url",
    "URL": "url",
    "商品链接": "url",
    "link": "url",
    "图片": "image_url",
    "图片链接": "image_url",
    "商品图片": "image_url",
    "image": "image_url",
    "备注": "notes",
    "note": "notes",
    "规格": "specs_text",
    "参数": "specs_text",
    "规格参数": "specs_text",
    "description": "raw_text",
    "描述": "raw_text",
    "正文": "raw_text",
    "原始文本": "raw_text",
    "raw": "raw_text",
    "服务": "service_text",
    "安装服务": "service_text",
    "配送安装": "service_text",
    "evidence": "evidence_text",
    "证据": "evidence_text",
    "解析证据": "evidence_text",
}

EXTRA_ADAPTER_FIELDS = [
    "evidence",
    "evidence_text",
    "manual_review_required",
    "missing_fields",
    "meta_description",
    "h1",
    "parse_success",
    "parse_error",
]

SIZE_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?(?:\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?)?\s*(?:mm|毫米|cm|厘米)?"
)
MATERIAL_KEYWORDS = ["材质", "钢制", "钢架", "钢木", "颗粒板", "板材", "玻璃", "金属", "铝合金", "不锈钢", "实木"]
INSTALLATION_KEYWORDS = ["安装", "现场安装", "上门安装", "装配"]
MIN_EVIDENCE_TEXT_LENGTH = 12
KNOWN_CANONICAL_FIELDS = set(PRODUCT_FIELDS + EXTRA_ADAPTER_FIELDS + ["adapter_source_type", "adapter_source_label"])


def clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_text(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


def canonicalize_product_item(item: dict[str, Any]) -> dict[str, Any]:
    canonical = dict(item)
    for source_key, target_key in FIELD_ALIASES.items():
        if source_key in item and target_key not in canonical:
            canonical[target_key] = item[source_key]
    return canonical


def has_explicit_source(item: dict[str, Any]) -> bool:
    return bool(_first_text(item.get("source"), item.get("platform"), item.get("source_name"), item.get("来源"), item.get("平台")))


def _combined_text(*items: dict[str, Any]) -> str:
    fields = [
        "title",
        "material",
        "dimensions",
        "specs_text",
        "service_text",
        "raw_text",
        "evidence_text",
        "evidence",
        "notes",
    ]
    parts: list[str] = []
    for item in items:
        for field in fields:
            text = clean_text(item.get(field))
            if text:
                parts.append(text)
    return " ".join(parts)


def _has_dimensions(text: str, product: dict[str, Any]) -> bool:
    return bool(clean_text(product.get("dimensions")) or SIZE_PATTERN.search(text) or "尺寸" in text)


def _has_material(text: str, product: dict[str, Any]) -> bool:
    return bool(clean_text(product.get("material")) or any(keyword in text for keyword in MATERIAL_KEYWORDS))


def _has_installation_service(text: str, product: dict[str, Any]) -> bool:
    service_text = clean_text(product.get("service_text"))
    return bool(any(keyword in service_text for keyword in INSTALLATION_KEYWORDS) or any(keyword in text for keyword in INSTALLATION_KEYWORDS))


def _evidence_text(product: dict[str, Any], raw_item: dict[str, Any] | None = None) -> str:
    raw_item = raw_item or {}
    return _first_text(
        product.get("evidence_text"),
        product.get("evidence"),
        raw_item.get("evidence_text"),
        raw_item.get("evidence"),
        product.get("raw_text"),
        raw_item.get("raw_text"),
        raw_item.get("description"),
        product.get("specs_text"),
        product.get("service_text"),
    )[:2000]


def _existing_missing_fields(product: dict[str, Any], raw_item: dict[str, Any] | None = None) -> list[str]:
    values: list[str] = []
    for item in [raw_item or {}, product]:
        missing = item.get("missing_fields")
        if isinstance(missing, list):
            values.extend(clean_text(field) for field in missing if clean_text(field))
    return values


def _extra_fields(item: dict[str, Any]) -> dict[str, str]:
    aliases = set(FIELD_ALIASES)
    extras: dict[str, str] = {}
    for key, value in item.items():
        if key in aliases or key in KNOWN_CANONICAL_FIELDS:
            continue
        text = clean_text(value)
        if text:
            extras[key] = text
    return extras


def assess_candidate_missing_fields(product: dict[str, Any], raw_item: dict[str, Any] | None = None) -> list[str]:
    raw_item = raw_item or product
    text = _combined_text(raw_item, product)
    missing: list[str] = _existing_missing_fields(product, raw_item)

    if product.get("price") in (None, ""):
        missing.append("price")
    if not _has_dimensions(text, product):
        missing.append("dimensions")
    if not _has_material(text, product):
        missing.append("material")
    if not _has_installation_service(text, product):
        missing.append("installation_service")
    if not has_explicit_source(raw_item):
        missing.append("source")
    if len(_evidence_text(product, raw_item)) < MIN_EVIDENCE_TEXT_LENGTH:
        missing.append("evidence_text")

    return list(dict.fromkeys(field for field in missing if field))


class ProductSourceAdapter(ABC):
    """Base interface for customer-provided product data sources."""

    source_type = "base"

    def __init__(self, source_label: str = "") -> None:
        self.source_label = source_label

    @abstractmethod
    def load_candidates(self) -> list[dict[str, Any]]:
        """Return normalized product candidates that can enter ranking and Word output."""

    def normalize_candidate(self, item: dict[str, Any]) -> dict[str, Any]:
        canonical_item = canonicalize_product_item(item)
        extra = _extra_fields(canonical_item)
        normalized = normalize_products([canonical_item])[0]

        if not has_explicit_source(canonical_item):
            normalized["source"] = ""
            normalized["platform"] = ""

        for field in EXTRA_ADAPTER_FIELDS:
            if field in canonical_item:
                normalized[field] = canonical_item[field]

        evidence_text = _evidence_text(normalized, canonical_item)
        normalized["evidence_text"] = evidence_text
        normalized["evidence"] = evidence_text
        normalized["adapter_source_type"] = self.source_type
        if self.source_label:
            normalized["adapter_source_label"] = self.source_label
        if extra:
            normalized["extra"] = extra

        missing_fields = assess_candidate_missing_fields(normalized, canonical_item)
        normalized["missing_fields"] = missing_fields
        normalized["manual_review_required"] = bool(missing_fields or canonical_item.get("manual_review_required"))
        normalized["parse_success"] = bool(clean_text(normalized.get("title")))
        if not normalized["parse_success"] and not clean_text(normalized.get("parse_error")):
            normalized["parse_error"] = "缺少商品标题，无法确认商品信息。"
            normalized["manual_review_required"] = True

        return normalized

    def normalize_candidates(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self.normalize_candidate(item) for item in items if isinstance(item, dict)]
