from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REVIEW_ITEMS_PATH = BASE_DIR / "outputs" / "manual_review_items.json"
DEFAULT_TEMPLATE_PATH = BASE_DIR / "outputs" / "manual_review_filled_template.json"

TEMPLATE_FIELDS = [
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
]


def _resolve_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else BASE_DIR / candidate


def _read_review_items(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or path.stat().st_size == 0:
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"人工复核清单 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

    if isinstance(data, dict):
        data = data.get("review_items", [])
    if not isinstance(data, list):
        raise ValueError("人工复核清单 JSON 顶层必须是数组，或包含 review_items 数组。")
    return [item for item in data if isinstance(item, dict)]


def _template_item(review_item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": review_item.get("title", ""),
        "url": review_item.get("url", ""),
        "source": review_item.get("source", ""),
        "missing_fields": review_item.get("missing_fields", []),
        "risk_reason": review_item.get("risk_reason", ""),
        "suggested_action": review_item.get("suggested_action", ""),
        "review_status": "",
        "review_note": "",
        "confirmed_price": "",
        "confirmed_dimensions": "",
        "confirmed_material": "",
        "confirmed_installation_service": "",
        "confirmed_source": "",
        "confirmed_evidence_text": "",
        "confirmed_fields": [],
    }


def generate_review_template(
    review_items_path: str | Path = DEFAULT_REVIEW_ITEMS_PATH,
    output_path: str | Path = DEFAULT_TEMPLATE_PATH,
) -> dict[str, list[dict[str, Any]]]:
    input_path = _resolve_path(review_items_path)
    resolved_output_path = _resolve_path(output_path)
    review_items = _read_review_items(input_path)
    template = {"review_items": [_template_item(item) for item in review_items]}

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8")
    return template


def main() -> int:
    try:
        template = generate_review_template()
    except Exception as exc:
        print(f"客户复核模板生成失败：{exc}")
        return 1

    print(f"客户复核模板项数量：{len(template['review_items'])}")
    print(f"客户复核模板：{DEFAULT_TEMPLATE_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
