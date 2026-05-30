from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import assess_candidate_missing_fields, clean_text
from src.crawler.review_template import DEFAULT_TEMPLATE_PATH, generate_review_template
from src.crawler.review_validate import DEFAULT_VALIDATION_REPORT_PATH, validate_review_filled, write_empty_validation_report


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTS_PATH = BASE_DIR / "outputs" / "crawler_products.json"
DEFAULT_MANUAL_REVIEW_PATH = BASE_DIR / "outputs" / "manual_review_items.json"
DEFAULT_REVIEWED_PRODUCTS_PATH = BASE_DIR / "outputs" / "reviewed_products.json"
DEFAULT_REVIEW_REPORT_PATH = BASE_DIR / "outputs" / "review_report.json"
NOTICE = "复核结果为人工补充的采购辅助信息，不代表最终采购结论。"

CONFIRMED_FIELD_TARGETS = {
    "confirmed_price": ("price",),
    "confirmed_dimensions": ("dimensions",),
    "confirmed_material": ("material",),
    "confirmed_source": ("source",),
    "confirmed_evidence_text": ("evidence_text", "evidence"),
}
CONFIRMED_FIELD_NAMES = {
    "confirmed_price": "price",
    "confirmed_dimensions": "dimensions",
    "confirmed_material": "material",
    "confirmed_installation_service": "installation_service",
    "confirmed_source": "source",
    "confirmed_evidence_text": "evidence_text",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"人工复核 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc


def _write_json(path: str | Path, data: Any) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def _has_confirmed_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(clean_text(value))
    if isinstance(value, (list, dict, tuple, set)):
        return bool(value)
    return True


def _load_products(products_path: str | Path) -> list[dict[str, Any]]:
    path = Path(products_path)
    if not path.exists() or path.stat().st_size == 0:
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"商品候选 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc
    if isinstance(data, dict) and isinstance(data.get("products"), list):
        data = data["products"]
    if not isinstance(data, list):
        raise ValueError("商品候选 JSON 顶层必须是数组，或包含 products 数组。")
    return [item for item in data if isinstance(item, dict)]


def load_review_filled(path: str | Path) -> list[dict[str, Any]]:
    review_path = Path(path)
    if not review_path.exists() or review_path.stat().st_size == 0:
        return []

    data = _read_json(review_path)
    if isinstance(data, dict):
        data = data.get("review_items")
    if not isinstance(data, list):
        raise ValueError("人工补齐 JSON 顶层必须是数组，或包含 review_items 数组。")
    return [item for item in data if isinstance(item, dict)]


def _url_key(value: Any) -> str:
    return clean_text(value).rstrip("/")


def _weak_key(title: Any, source: Any) -> tuple[str, str]:
    return (clean_text(title).casefold(), clean_text(source).casefold())


def _source_text(product: dict[str, Any]) -> str:
    return clean_text(product.get("source") or product.get("platform") or product.get("adapter_source_label"))


def _build_indexes(products: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[tuple[str, str], dict[str, Any]]]:
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


def _match_product(
    review_item: dict[str, Any],
    by_url: dict[str, dict[str, Any]],
    by_title_source: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any] | None:
    review_url = _url_key(review_item.get("url"))
    if review_url:
        return by_url.get(review_url)

    review_key = _weak_key(review_item.get("title"), review_item.get("source"))
    if all(review_key):
        return by_title_source.get(review_key)
    return None


def _parse_confirmed_fields(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_fields = value
    elif isinstance(value, str):
        raw_fields = value.replace("，", ",").replace("；", ",").replace(";", ",").split(",")
    else:
        raw_fields = []
    return list(dict.fromkeys(clean_text(field) for field in raw_fields if clean_text(field)))


def _installation_target(product: dict[str, Any]) -> str:
    if "service_text" in product or "installation_service" not in product:
        return "service_text"
    return "installation_service"


def _review_summary(review_item: dict[str, Any], matched: bool) -> dict[str, Any]:
    return {
        "title": clean_text(review_item.get("title")),
        "url": clean_text(review_item.get("url")),
        "source": clean_text(review_item.get("source")),
        "review_status": clean_text(review_item.get("review_status")),
        "review_note": clean_text(review_item.get("review_note")),
        "matched": matched,
    }


def _remaining_missing_fields(product: dict[str, Any]) -> list[str]:
    candidate = dict(product)
    candidate.pop("missing_fields", None)
    raw_candidate = dict(candidate)
    raw_candidate.pop("missing_fields", None)
    return assess_candidate_missing_fields(candidate, raw_candidate)


def _apply_confirmed_fields(product: dict[str, Any], review_item: dict[str, Any]) -> tuple[dict[str, Any], list[str], int]:
    updated_product = dict(product)
    reviewed_fields = _parse_confirmed_fields(review_item.get("confirmed_fields"))
    update_count = 0

    for confirmed_key, targets in CONFIRMED_FIELD_TARGETS.items():
        if not _has_confirmed_value(review_item.get(confirmed_key)):
            continue
        value = review_item[confirmed_key]
        for target in targets:
            if updated_product.get(target) != value:
                updated_product[target] = value
                update_count += 1
        reviewed_fields.append(CONFIRMED_FIELD_NAMES[confirmed_key])

    if _has_confirmed_value(review_item.get("confirmed_installation_service")):
        target = _installation_target(updated_product)
        value = review_item["confirmed_installation_service"]
        if updated_product.get(target) != value:
            updated_product[target] = value
            update_count += 1
        reviewed_fields.append("installation_service")

    return updated_product, list(dict.fromkeys(reviewed_fields)), update_count


def _empty_report(
    products_path: str | Path,
    review_filled_path: str | Path | None,
    output_products_path: str | Path,
    output_report_path: str | Path,
    notice: str = NOTICE,
) -> dict[str, Any]:
    return {
        "total_review_items": 0,
        "approved_count": 0,
        "rejected_count": 0,
        "needs_more_info_count": 0,
        "reviewed_products_count": 0,
        "unresolved_items": [],
        "rejected_items": [],
        "unmatched_review_items": [],
        "field_updates_count": 0,
        "input_paths": {
            "products": str(products_path),
            "review_filled": str(review_filled_path or ""),
        },
        "output_paths": {
            "reviewed_products": str(output_products_path),
            "review_report": str(output_report_path),
        },
        "notice": notice,
    }


def write_empty_review_outputs(
    products_path: str | Path = DEFAULT_PRODUCTS_PATH,
    review_filled_path: str | Path | None = None,
    output_products_path: str | Path = DEFAULT_REVIEWED_PRODUCTS_PATH,
    output_report_path: str | Path = DEFAULT_REVIEW_REPORT_PATH,
) -> dict[str, Any]:
    report = _empty_report(products_path, review_filled_path, output_products_path, output_report_path)
    _write_json(output_products_path, [])
    _write_json(output_report_path, report)
    return report


def _validation_report_path_for(output_report_path: str | Path) -> Path:
    resolved_output_report_path = Path(output_report_path)
    if resolved_output_report_path == DEFAULT_REVIEW_REPORT_PATH:
        return DEFAULT_VALIDATION_REPORT_PATH
    return resolved_output_report_path.with_name(DEFAULT_VALIDATION_REPORT_PATH.name)


def _raise_for_validation_errors(validation_report: dict[str, Any]) -> None:
    if not validation_report.get("error_count"):
        return

    messages = []
    for error in validation_report.get("errors", []):
        if not isinstance(error, dict):
            continue
        item_index = error.get("item_index")
        field = error.get("field")
        message = error.get("message")
        prefix = f"第 {item_index} 项" if item_index else "复核文件"
        if field:
            prefix = f"{prefix} {field}"
        messages.append(f"{prefix}：{message}")
    detail = "；".join(messages) if messages else "请查看人工复核校验报告。"
    raise ValueError(f"人工复核填写文件存在严重格式错误，已停止回填：{detail}")


def apply_manual_reviews(
    products_path: str | Path,
    review_filled_path: str | Path,
    output_products_path: str | Path = DEFAULT_REVIEWED_PRODUCTS_PATH,
    output_report_path: str | Path = DEFAULT_REVIEW_REPORT_PATH,
) -> dict[str, Any]:
    validation_report = validate_review_filled(
        review_filled_path,
        products_path=products_path,
        output_report_path=_validation_report_path_for(output_report_path),
    )
    _raise_for_validation_errors(validation_report)

    products = _load_products(products_path)
    review_items = load_review_filled(review_filled_path)
    if not review_items:
        return write_empty_review_outputs(products_path, review_filled_path, output_products_path, output_report_path)

    by_url, by_title_source = _build_indexes(products)
    reviewed_products: list[dict[str, Any]] = []
    unresolved_items: list[dict[str, Any]] = []
    rejected_items: list[dict[str, Any]] = []
    unmatched_review_items: list[dict[str, Any]] = []
    field_updates_count = 0
    reviewed_at = _utc_now()

    status_counts = {
        "approved": 0,
        "rejected": 0,
        "needs_more_info": 0,
    }

    for review_item in review_items:
        status = clean_text(review_item.get("review_status")).casefold()
        if status in status_counts:
            status_counts[status] += 1

        matched_product = _match_product(review_item, by_url, by_title_source)
        if matched_product is None:
            unmatched_review_items.append(_review_summary(review_item, matched=False))
            continue

        summary = _review_summary(review_item, matched=True)
        if status == "rejected":
            rejected_items.append(summary)
            continue
        if status != "approved":
            unresolved_items.append(summary)
            continue

        updated_product, reviewed_fields, update_count = _apply_confirmed_fields(matched_product, review_item)
        field_updates_count += update_count
        remaining_missing_fields = _remaining_missing_fields(updated_product)
        updated_product.update(
            {
                "review_status": "approved",
                "review_note": clean_text(review_item.get("review_note")),
                "reviewed_at": reviewed_at,
                "reviewed_fields": reviewed_fields,
                "manual_review_required": bool(remaining_missing_fields),
                "remaining_missing_fields": remaining_missing_fields,
                "review_source": str(review_filled_path),
            }
        )
        reviewed_products.append(updated_product)

    report = {
        "total_review_items": len(review_items),
        "approved_count": status_counts["approved"],
        "rejected_count": status_counts["rejected"],
        "needs_more_info_count": status_counts["needs_more_info"],
        "reviewed_products_count": len(reviewed_products),
        "unresolved_items": unresolved_items,
        "rejected_items": rejected_items,
        "unmatched_review_items": unmatched_review_items,
        "field_updates_count": field_updates_count,
        "input_paths": {
            "products": str(products_path),
            "review_filled": str(review_filled_path),
        },
        "output_paths": {
            "reviewed_products": str(output_products_path),
            "review_report": str(output_report_path),
        },
        "notice": NOTICE,
    }

    _write_json(output_products_path, reviewed_products)
    _write_json(output_report_path, report)
    return report


def main() -> int:
    data_review_path = BASE_DIR / "data" / "manual_review_filled.json"
    output_review_path = BASE_DIR / "outputs" / "manual_review_filled.json"
    if data_review_path.exists():
        review_filled_path: Path | None = data_review_path
    elif output_review_path.exists():
        review_filled_path = output_review_path
    else:
        review_filled_path = None

    try:
        template = generate_review_template(DEFAULT_MANUAL_REVIEW_PATH, DEFAULT_TEMPLATE_PATH)
        if review_filled_path is not None:
            report = apply_manual_reviews(DEFAULT_PRODUCTS_PATH, review_filled_path)
        else:
            write_empty_validation_report(review_filled_path, DEFAULT_PRODUCTS_PATH, DEFAULT_VALIDATION_REPORT_PATH)
            report = write_empty_review_outputs(DEFAULT_PRODUCTS_PATH, review_filled_path)
    except Exception as exc:
        print(f"人工复核回填失败：{exc}")
        return 1

    print(f"客户复核模板项数量：{len(template['review_items'])}")
    print(f"客户复核模板：{DEFAULT_TEMPLATE_PATH}")
    print(f"已复核商品数量：{report['reviewed_products_count']}")
    print(f"复核校验报告：{DEFAULT_VALIDATION_REPORT_PATH}")
    print(f"复核报告：{report['output_paths']['review_report']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
