from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import clean_text


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTS_PATH = BASE_DIR / "outputs" / "crawler_products.json"
DEFAULT_VALIDATION_REPORT_PATH = BASE_DIR / "outputs" / "manual_review_validation_report.json"
DEFAULT_REVIEW_FILLED_PATHS = (
    BASE_DIR / "data" / "manual_review_filled.json",
    BASE_DIR / "outputs" / "manual_review_filled.json",
)
NOTICE = "校验结果仅用于辅助人工复核，不代表最终采购结论。"

ALLOWED_STATUSES = {"", "approved", "rejected", "needs_more_info"}
CONFIRMED_VALUE_FIELDS = [
    "confirmed_price",
    "confirmed_dimensions",
    "confirmed_material",
    "confirmed_installation_service",
    "confirmed_source",
    "confirmed_evidence_text",
]
KNOWN_REVIEW_FIELDS = {
    "title",
    "url",
    "source",
    "missing_fields",
    "risk_reason",
    "suggested_action",
    "review_status",
    "review_note",
    "confirmed_price",
    "confirmed_dimensions",
    "confirmed_material",
    "confirmed_installation_service",
    "confirmed_source",
    "confirmed_evidence_text",
    "confirmed_fields",
}


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc


def _load_review_items(path: Path) -> list[Any]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    data = _read_json(path, "人工复核填写文件")
    if isinstance(data, dict):
        data = data.get("review_items")
    if not isinstance(data, list):
        raise ValueError("人工复核填写文件顶层必须是数组，或包含 review_items 数组。")
    return data


def _load_products(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    data = _read_json(path, "商品候选文件")
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        data = data["products"]
    if not isinstance(data, list):
        raise ValueError("商品候选文件顶层必须是数组，或包含 products 数组。")
    return [item for item in data if isinstance(item, dict)]


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(clean_text(value))
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _url_key(value: Any) -> str:
    return clean_text(value).rstrip("/")


def _weak_key(title: Any, source: Any) -> tuple[str, str]:
    return (clean_text(title).casefold(), clean_text(source).casefold())


def _source_text(product: dict[str, Any]) -> str:
    return clean_text(product.get("source") or product.get("platform") or product.get("adapter_source_label"))


def _item_summary(index: int, item: dict[str, Any]) -> dict[str, Any]:
    return {
        "item_index": index,
        "title": clean_text(item.get("title")),
        "url": clean_text(item.get("url")),
        "source": clean_text(item.get("source")),
    }


def _add_issue(
    container: list[dict[str, Any]],
    index: int,
    item: dict[str, Any],
    field: str,
    message: str,
    code: str,
) -> dict[str, Any]:
    issue = _item_summary(index, item)
    issue.update({"field": field, "code": code, "message": message})
    container.append(issue)
    return issue


def _parse_confirmed_fields(value: Any) -> tuple[list[str], str]:
    if value is None:
        return [], ""
    if isinstance(value, list):
        return list(dict.fromkeys(clean_text(field) for field in value if clean_text(field))), ""
    if isinstance(value, str):
        text = clean_text(value)
        if not text:
            return [], ""
        if text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as exc:
                return [], f"confirmed_fields 字符串不是可解析数组：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}"
            if not isinstance(parsed, list):
                return [], "confirmed_fields 字符串解析后必须是数组。"
            return list(dict.fromkeys(clean_text(field) for field in parsed if clean_text(field))), ""
        if text.startswith("{"):
            return [], "confirmed_fields 不能填写为对象；请填写数组或用逗号分隔的字段名。"
        parts = text.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
        return list(dict.fromkeys(clean_text(field) for field in parts if clean_text(field))), ""
    return [], "confirmed_fields 必须是数组，或可解析为字段列表的字符串。"


def _build_product_indexes(
    products: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
    by_url: dict[str, dict[str, Any]] = {}
    by_title_source: dict[tuple[str, str], dict[str, Any]] = {}
    for product in products:
        url_key = _url_key(product.get("url"))
        if url_key and url_key not in by_url:
            by_url[url_key] = product

        weak_key = _weak_key(product.get("title"), _source_text(product))
        if all(weak_key) and weak_key not in by_title_source:
            by_title_source[weak_key] = product
    return by_url, by_title_source


def _matched_product(
    review_item: dict[str, Any],
    by_url: dict[str, dict[str, Any]],
    by_title_source: dict[tuple[str, str], dict[str, Any]],
) -> bool:
    review_url = _url_key(review_item.get("url"))
    if review_url:
        return review_url in by_url

    weak_key = _weak_key(review_item.get("title"), review_item.get("source"))
    if all(weak_key):
        return weak_key in by_title_source
    return False


def _duplicate_key(item: dict[str, Any]) -> tuple[str, str] | None:
    url_key = _url_key(item.get("url"))
    if url_key:
        return ("url", url_key)
    weak_key = _weak_key(item.get("title"), item.get("source"))
    if all(weak_key):
        return ("title_source", "|".join(weak_key))
    return None


def _base_report(
    review_filled_path: str | Path | None,
    products_path: str | Path,
    output_report_path: str | Path,
) -> dict[str, Any]:
    return {
        "total_items": 0,
        "valid_items_count": 0,
        "error_count": 0,
        "warning_count": 0,
        "errors": [],
        "warnings": [],
        "duplicate_items": [],
        "unmatched_items": [],
        "incomplete_items": [],
        "unknown_field_items": [],
        "input_paths": {
            "review_filled": str(review_filled_path or ""),
            "products": str(products_path),
        },
        "output_paths": {
            "validation_report": str(output_report_path),
        },
        "notice": NOTICE,
    }


def write_empty_validation_report(
    review_filled_path: str | Path | None = None,
    products_path: str | Path = DEFAULT_PRODUCTS_PATH,
    output_report_path: str | Path = DEFAULT_VALIDATION_REPORT_PATH,
) -> dict[str, Any]:
    report_path = _resolve_path(output_report_path)
    report = _base_report(review_filled_path, products_path, report_path)
    if review_filled_path is None:
        report["warnings"].append(
            {
                "item_index": None,
                "field": "review_filled",
                "code": "missing_review_filled_file",
                "message": "未发现客户填写后的人工复核文件，本次没有可校验的复核项。",
            }
        )
        report["warning_count"] = len(report["warnings"])
    _write_json(report_path, report)
    return report


def validate_review_filled(
    review_filled_path: str | Path,
    products_path: str | Path = DEFAULT_PRODUCTS_PATH,
    output_report_path: str | Path = DEFAULT_VALIDATION_REPORT_PATH,
) -> dict[str, Any]:
    review_path = _resolve_path(review_filled_path)
    product_path = _resolve_path(products_path)
    report_path = _resolve_path(output_report_path)

    review_items = _load_review_items(review_path)
    products = _load_products(product_path)
    by_url, by_title_source = _build_product_indexes(products)
    report = _base_report(review_path, product_path, report_path)
    report["total_items"] = len(review_items)

    error_item_indexes: set[int] = set()
    seen_keys: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}

    for index, raw_item in enumerate(review_items, start=1):
        if not isinstance(raw_item, dict):
            placeholder = {"title": "", "url": "", "source": ""}
            _add_issue(report["errors"], index, placeholder, "review_item", "该复核项不是对象，请按模板填写每一条复核记录。", "invalid_item_type")
            error_item_indexes.add(index)
            continue

        item = raw_item
        status = clean_text(item.get("review_status")).casefold()
        confirmed_fields, confirmed_fields_error = _parse_confirmed_fields(item.get("confirmed_fields"))

        if status not in ALLOWED_STATUSES:
            _add_issue(
                report["errors"],
                index,
                item,
                "review_status",
                "review_status 只能填写 approved、rejected、needs_more_info，或留空。",
                "invalid_review_status",
            )
            error_item_indexes.add(index)

        if confirmed_fields_error:
            _add_issue(report["errors"], index, item, "confirmed_fields", confirmed_fields_error, "invalid_confirmed_fields")
            error_item_indexes.add(index)

        unknown_fields = sorted(str(field) for field in item if field not in KNOWN_REVIEW_FIELDS)
        if unknown_fields:
            unknown_item = _item_summary(index, item)
            unknown_item.update(
                {
                    "unknown_fields": unknown_fields,
                    "message": "发现模板外字段，校验器已忽略这些字段；如需复核，请填写到 review_note 或对应 confirmed_* 字段。",
                }
            )
            report["unknown_field_items"].append(unknown_item)
            report["warnings"].append(
                {
                    **unknown_item,
                    "field": "unknown_fields",
                    "code": "unknown_fields",
                }
            )

        duplicate_key = _duplicate_key(item)
        if duplicate_key is not None:
            first_seen = seen_keys.get(duplicate_key)
            if first_seen is None:
                seen_keys[duplicate_key] = (index, item)
            else:
                first_index, first_item = first_seen
                duplicate_item = _item_summary(index, item)
                duplicate_item.update(
                    {
                        "duplicate_with_item_index": first_index,
                        "match_key_type": duplicate_key[0],
                        "match_key_value": duplicate_key[1],
                        "message": "发现重复复核项，请只保留一条最终确认记录，避免重复回填。",
                    }
                )
                duplicate_item["duplicate_with"] = _item_summary(first_index, first_item)
                report["duplicate_items"].append(duplicate_item)
                report["warnings"].append(
                    {
                        **duplicate_item,
                        "field": "review_item",
                        "code": "duplicate_review_item",
                    }
                )

        if not _matched_product(item, by_url, by_title_source):
            unmatched_item = _item_summary(index, item)
            unmatched_item["message"] = "该复核项未能匹配到当前候选商品，请确认 title/url/source 是否保留自原始复核清单。"
            report["unmatched_items"].append(unmatched_item)
            report["warnings"].append(
                {
                    **unmatched_item,
                    "field": "review_item",
                    "code": "unmatched_review_item",
                }
            )

        if not status:
            incomplete_item = _item_summary(index, item)
            incomplete_item["message"] = "review_status 为空，请填写 approved、rejected 或 needs_more_info。"
            report["incomplete_items"].append(incomplete_item)
            report["warnings"].append(
                {
                    **incomplete_item,
                    "field": "review_status",
                    "code": "incomplete_review_status",
                }
            )

        has_confirmed_value = any(_has_value(item.get(field)) for field in CONFIRMED_VALUE_FIELDS) or bool(confirmed_fields)
        if status == "approved" and not has_confirmed_value:
            _add_issue(
                report["warnings"],
                index,
                item,
                "confirmed_fields",
                "approved 状态建议至少填写一个 confirmed_* 字段，或在 confirmed_fields 中列出已确认字段。",
                "approved_without_confirmed_fields",
            )

        if status == "rejected" and not clean_text(item.get("review_note")):
            _add_issue(report["warnings"], index, item, "review_note", "rejected 状态建议填写 review_note，说明驳回原因。", "rejected_without_note")

        if status == "needs_more_info" and not clean_text(item.get("review_note")):
            _add_issue(
                report["warnings"],
                index,
                item,
                "review_note",
                "needs_more_info 状态建议填写 review_note，说明还需要客户补充什么信息。",
                "needs_more_info_without_note",
            )

    report["error_count"] = len(report["errors"])
    report["warning_count"] = len(report["warnings"])
    report["valid_items_count"] = max(0, len(review_items) - len(error_item_indexes))

    _write_json(report_path, report)
    return report


def _select_review_filled_path() -> Path | None:
    for path in DEFAULT_REVIEW_FILLED_PATHS:
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def main() -> int:
    review_filled_path = _select_review_filled_path()
    try:
        if review_filled_path is None:
            report = write_empty_validation_report()
        else:
            report = validate_review_filled(review_filled_path)
    except Exception as exc:
        print(f"人工复核填写校验失败：{exc}")
        return 1

    print(f"校验复核项数量：{report['total_items']}")
    print(f"错误数量：{report['error_count']}")
    print(f"警告数量：{report['warning_count']}")
    print(f"校验报告：{report['output_paths']['validation_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
