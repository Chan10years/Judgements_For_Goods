from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.crawler.adapters.base import assess_candidate_missing_fields, clean_text
from src.crawler.review_apply import apply_manual_reviews, write_empty_review_outputs


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_PRODUCTS_PATH = BASE_DIR / "outputs" / "crawler_products.json"
DEFAULT_MANUAL_REVIEW_PATH = BASE_DIR / "outputs" / "manual_review_items.json"
DEFAULT_REVIEWED_PRODUCTS_PATH = BASE_DIR / "outputs" / "reviewed_products.json"
DEFAULT_REVIEW_REPORT_PATH = BASE_DIR / "outputs" / "review_report.json"
DEFAULT_REVIEW_FILLED_PATHS = (
    BASE_DIR / "data" / "manual_review_filled.json",
    BASE_DIR / "outputs" / "manual_review_filled.json",
)

FIELD_RISK_REASONS = {
    "price": "缺少可核验价格。",
    "dimensions": "缺少可核验尺寸。",
    "material": "缺少可核验材质。",
    "installation_service": "缺少明确安装服务说明。",
    "source": "缺少明确商品来源。",
    "evidence_text": "解析证据不足。",
    "title": "缺少商品标题。",
    "specs_text": "缺少规格参数文本。",
    "service_text": "缺少服务文本。",
}


def _load_products(products_or_path: str | Path | list[dict[str, Any]] | dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(products_or_path, list):
        return [item for item in products_or_path if isinstance(item, dict)]
    if isinstance(products_or_path, dict):
        products = products_or_path.get("products", [])
        return [item for item in products if isinstance(item, dict)] if isinstance(products, list) else []

    path = Path(products_or_path)
    if not path.exists():
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


def _evidence_text(product: dict[str, Any]) -> str:
    return clean_text(product.get("evidence_text") or product.get("evidence") or product.get("raw_text"))[:2000]


def _risk_reason(product: dict[str, Any], missing_fields: list[str]) -> str:
    reasons = [FIELD_RISK_REASONS.get(field, f"字段 {field} 需人工确认。") for field in missing_fields]
    parse_error = clean_text(product.get("parse_error"))
    if parse_error:
        reasons.append(parse_error)
    if product.get("manual_review_required") and not reasons:
        reasons.append("上游数据源已标记该商品需人工复核。")
    return "；".join(dict.fromkeys(reasons))


def _suggested_action(missing_fields: list[str]) -> str:
    actions = []
    if "price" in missing_fields:
        actions.append("确认价格是否含税、含运费")
    if "dimensions" in missing_fields:
        actions.append("核对尺寸参数")
    if "material" in missing_fields:
        actions.append("核对材质证明或页面参数")
    if "installation_service" in missing_fields:
        actions.append("确认是否包含配送和现场安装服务")
    if "source" in missing_fields:
        actions.append("补充明确来源或原始链接")
    if "evidence_text" in missing_fields:
        actions.append("补充可核验的页面截图、参数页或客户原始资料")
    if not actions:
        actions.append("核对上游标记的复核原因")
    return "请人工" + "；".join(actions) + "，复核后再作为采购辅助候选使用。"


def build_manual_review_items(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    review_items: list[dict[str, Any]] = []

    for product in products:
        if not isinstance(product, dict):
            continue
        missing_fields = assess_candidate_missing_fields(product)
        parse_failed = product.get("parse_success") is False
        manual_flagged = bool(product.get("manual_review_required"))
        if not missing_fields and not parse_failed and not manual_flagged:
            continue

        title = clean_text(product.get("title"))
        review_items.append(
            {
                "title": title,
                "url": clean_text(product.get("url")),
                "source": clean_text(product.get("source") or product.get("platform")),
                "missing_fields": missing_fields,
                "manual_review_required": True,
                "evidence_text": _evidence_text(product),
                "risk_reason": _risk_reason(product, missing_fields),
                "suggested_action": _suggested_action(missing_fields),
            }
        )

    return review_items


def write_manual_review_items(review_items: list[dict[str, Any]], output_path: str | Path = DEFAULT_MANUAL_REVIEW_PATH) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(review_items, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def generate_manual_review_items(
    products_or_path: str | Path | list[dict[str, Any]] | dict[str, Any] = DEFAULT_PRODUCTS_PATH,
    output_path: str | Path = DEFAULT_MANUAL_REVIEW_PATH,
) -> list[dict[str, Any]]:
    products = _load_products(products_or_path)
    review_items = build_manual_review_items(products)
    write_manual_review_items(review_items, output_path)
    return review_items


def _select_review_filled_path() -> Path | None:
    for path in DEFAULT_REVIEW_FILLED_PATHS:
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def main() -> int:
    try:
        review_items = generate_manual_review_items()
        review_filled_path = _select_review_filled_path()
        if review_filled_path is not None:
            review_report = apply_manual_reviews(
                DEFAULT_PRODUCTS_PATH,
                review_filled_path,
                output_products_path=DEFAULT_REVIEWED_PRODUCTS_PATH,
                output_report_path=DEFAULT_REVIEW_REPORT_PATH,
            )
        else:
            review_report = write_empty_review_outputs(
                DEFAULT_PRODUCTS_PATH,
                review_filled_path,
                output_products_path=DEFAULT_REVIEWED_PRODUCTS_PATH,
                output_report_path=DEFAULT_REVIEW_REPORT_PATH,
            )
    except Exception as exc:
        print(f"人工复核清单生成失败：{exc}")
        return 1

    print(f"人工复核项数量：{len(review_items)}")
    print(f"人工复核清单：{DEFAULT_MANUAL_REVIEW_PATH}")
    print(f"已复核商品数量：{review_report['reviewed_products_count']}")
    print(f"复核报告：{DEFAULT_REVIEW_REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
