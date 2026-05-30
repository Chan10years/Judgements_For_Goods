from pathlib import Path
from typing import Any
import json
import re
from urllib.parse import quote

from src.crawler.adapters.manual_csv_adapter import ManualCsvAdapter
from src.crawler.adapters.manual_json_adapter import ManualJsonAdapter
from src.doc_parser import parse_requirements, save_requirements_json
from src.doc_writer import write_responses
from src.product_loader import load_products_json
from src.product_ranker import collect_requirement_text, rank_products, save_ranked_products_json
from src.response_builder import build_recommendation_responses, save_responses_json, select_top_products
from src.sourcing_assistant import (
    build_marketplace_search_links as build_smart_marketplace_search_links,
    enrich_ranked_products_with_sourcing_guidance,
    load_candidate_mixed_text_file,
    write_scoring_csv,
)


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs"

DEFAULT_WORD_PATH = DATA_DIR / "办公屏风01模板样例.docx"
DEFAULT_SAMPLE_PRODUCTS_PATH = DATA_DIR / "sample_products.json"
DEFAULT_CRAWLER_PRODUCTS_PATH = OUTPUT_DIR / "crawler_products.json"
DEFAULT_MANUAL_REVIEW_PATH = OUTPUT_DIR / "manual_review_items.json"
DEFAULT_REVIEWED_PRODUCTS_PATH = OUTPUT_DIR / "reviewed_products.json"
DEFAULT_REVIEW_REPORT_PATH = OUTPUT_DIR / "review_report.json"
REQUIREMENTS_JSON = OUTPUT_DIR / "requirements.json"
RANKED_PRODUCTS_JSON = OUTPUT_DIR / "ranked_products.json"
RESPONSES_JSON = OUTPUT_DIR / "responses.json"
OUTPUT_DOCX = OUTPUT_DIR / "recommendation_result.docx"
SOURCING_SCORE_TABLE_CSV = OUTPUT_DIR / "sourcing_score_table.csv"
_REVIEWED_PATH_UNSET = object()
DATA_SOURCE_PRIORITY = ["reviewed_products.json", "crawler_products.json", "sample_products.json"]
DELIVERY_OUTPUT_FILE_INDEX = [
    "outputs/recommendation_result.docx",
    "outputs/ranked_products.json",
    "outputs/responses.json",
    "outputs/crawler_products.json",
    "outputs/manual_review_items.json",
    "outputs/manual_review_filled_template.json",
    "outputs/manual_review_validation_report.json",
    "outputs/reviewed_products.json",
    "outputs/review_report.json",
    "outputs/sourcing_score_table.csv",
]
STAGE13_2B_MISSING_FIELD_LABELS = {
    "title": "商品名称",
    "platform": "平台",
    "price": "价格",
    "url": "商品链接",
    "shop": "店铺",
    "source": "来源",
    "dimensions": "尺寸",
    "material": "材质",
    "color": "颜色",
    "installation_service": "安装服务",
    "image_url": "图片链接",
    "specs_text": "规格参数",
    "service_text": "服务说明",
    "evidence_text": "证据文本",
}
_DIMENSION_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?(?:\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?)?\s*(?:mm|毫米|cm|厘米)?"
)
_SEARCH_KEYWORD_HINTS = ["办公屏风", "屏风", "工位", "隔断", "办公桌", "卡位", "卡座"]
_MATERIAL_SEARCH_HINTS = ["钢制", "钢架", "钢木", "颗粒板", "玻璃", "铝合金"]
_URL_PATTERN = re.compile(r"https?://[^\s,，;；]+", re.IGNORECASE)
_PRICE_PATTERN = re.compile(r"(?:价格|价|￥|¥)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|块)")
_MATERIAL_HINTS = ["钢制框架", "钢制", "钢架", "钢木", "颗粒板", "实木颗粒板", "玻璃", "铝合金", "不锈钢", "板材"]
_INSTALLATION_HINTS = ["现场安装", "上门安装", "安装", "配送安装", "送货", "配送"]


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label}不存在：{path}")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(_text(value))
    return True


def _candidate_extra(candidate: dict[str, Any]) -> dict[str, Any]:
    extra = candidate.get("extra")
    return extra if isinstance(extra, dict) else {}


def _read_text_with_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk")


def _detect_platform_from_url(url: str) -> str:
    lowered = url.lower()
    if "jd.com" in lowered or "jingdong" in lowered:
        return "京东"
    if "taobao.com" in lowered:
        return "淘宝"
    if "tmall.com" in lowered:
        return "天猫"
    return "客户候选链接"


def _strip_urls(text: str) -> str:
    return _text(_URL_PATTERN.sub(" ", text))


def _extract_price_from_text(text: str) -> int | float | None:
    without_urls = _strip_urls(text)
    for match in _PRICE_PATTERN.finditer(without_urls):
        value = match.group(1) or match.group(2)
        try:
            number = float(value)
        except ValueError:
            continue
        if number <= 0 or number > 1_000_000:
            continue
        return int(number) if number.is_integer() else number
    return None


def _extract_material_from_text(text: str) -> str:
    matched = [keyword for keyword in _MATERIAL_HINTS if keyword in text]
    return "，".join(dict.fromkeys(matched))


def _extract_installation_from_text(text: str) -> str:
    matched = [keyword for keyword in _INSTALLATION_HINTS if keyword in text]
    return "，".join(dict.fromkeys(matched))


def _extract_link_title(line_text: str, platform: str) -> tuple[str, bool]:
    text_without_url = _strip_urls(line_text)
    text_without_price = re.sub(r"(?:价格|价|￥|¥)?\s*\d+(?:\.\d+)?\s*(?:元|块)?", " ", text_without_url)
    dimension = _DIMENSION_PATTERN.search(text_without_price)
    if dimension:
        text_without_price = text_without_price.replace(dimension.group(0), " ")
    for keyword in _MATERIAL_HINTS + _INSTALLATION_HINTS:
        text_without_price = text_without_price.replace(keyword, " ")
    title = _text(text_without_price.strip(" ,-，;；|"))
    if title:
        return title[:120], False
    return f"待人工复核候选商品（{platform}链接）", True


def load_candidate_links_file(path: str | Path) -> list[dict[str, Any]]:
    """Parse customer-confirmed candidate links without fetching platform pages."""
    candidate_path = Path(path)
    products = load_candidate_mixed_text_file(candidate_path)
    for item in products:
        item["adapter_source_type"] = "manual_link_list"
        item["adapter_source_label"] = "客户候选链接清单"
        if item.get("source") == "客户候选链接/文本":
            item["source"] = "客户候选链接清单"
    return [_normalize_stage13_2b_candidate(item) for item in products]


def _normalize_stage13_2b_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    extra = _candidate_extra(normalized)

    installation_service = _first_text(
        normalized.get("installation_service"),
        extra.get("installation_service"),
        normalized.get("service_text"),
    )
    if installation_service:
        normalized["installation_service"] = installation_service
        if not _text(normalized.get("service_text")):
            normalized["service_text"] = installation_service

    evidence_text = _first_text(
        normalized.get("evidence_text"),
        extra.get("evidence_text"),
        normalized.get("evidence"),
        extra.get("evidence"),
    )
    if evidence_text:
        normalized["evidence_text"] = evidence_text
        normalized["evidence"] = evidence_text

    missing_fields = list(normalized.get("missing_fields") or [])
    field_values = {
        "title": "" if normalized.get("title_is_placeholder") else normalized.get("title"),
        "platform": _first_text(normalized.get("platform"), normalized.get("source")),
        "price": normalized.get("price"),
        "url": normalized.get("url"),
        "source": _first_text(normalized.get("source"), normalized.get("platform")),
        "dimensions": normalized.get("dimensions"),
        "material": normalized.get("material"),
        "installation_service": _first_text(normalized.get("installation_service"), normalized.get("service_text")),
        "image_url": normalized.get("image_url"),
        "specs_text": normalized.get("specs_text"),
        "evidence_text": normalized.get("evidence_text"),
    }
    for field, value in field_values.items():
        if _has_value(value):
            missing_fields = [item for item in missing_fields if item != field]
        elif field not in missing_fields:
            missing_fields.append(field)

    normalized["missing_fields"] = list(dict.fromkeys(_text(field) for field in missing_fields if _text(field)))
    normalized["manual_review_required"] = bool(normalized["missing_fields"] or normalized.get("manual_review_required"))

    if normalized["missing_fields"]:
        labels = [STAGE13_2B_MISSING_FIELD_LABELS.get(field, field) for field in normalized["missing_fields"]]
        review_note = "待人工复核字段：" + "、".join(labels)
        normalized["notes"] = f"{normalized['notes']}；{review_note}" if _text(normalized.get("notes")) else review_note

    return normalized


def load_candidate_products_file(path: str | Path) -> list[dict[str, Any]]:
    """Load customer candidate products through manual adapters or link lists."""
    candidate_path = Path(path)
    suffix = candidate_path.suffix.lower()

    if suffix == ".json":
        adapter = ManualJsonAdapter(candidate_path, source_label="客户上传 JSON")
        return [_normalize_stage13_2b_candidate(item) for item in adapter.load_candidates()]
    elif suffix == ".csv":
        try:
            adapter = ManualCsvAdapter(candidate_path, source_label="客户上传 CSV")
            return [_normalize_stage13_2b_candidate(item) for item in adapter.load_candidates()]
        except UnicodeDecodeError:
            adapter = ManualCsvAdapter(candidate_path, source_label="客户上传 CSV", encoding="gbk")
            return [_normalize_stage13_2b_candidate(item) for item in adapter.load_candidates()]
    elif suffix in {".txt", ".links"}:
        return load_candidate_links_file(candidate_path)
    else:
        raise ValueError("候选商品文件仅支持 JSON、CSV 或 TXT 链接清单。")


def save_candidate_products_json(products: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"products": products}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def build_marketplace_search_links(requirements: Any = None, default_keyword: str = "办公屏风 工位") -> dict[str, Any]:
    return build_smart_marketplace_search_links(requirements, default_keyword=default_keyword)


def _is_usable_product(item: Any, require_traceable_source: bool) -> bool:
    if not isinstance(item, dict):
        return False
    if not _text(item.get("title")):
        return False
    if not require_traceable_source:
        return True
    return any(_text(item.get(field)) for field in ["url", "source", "platform"])


def _is_usable_crawler_product(item: Any) -> bool:
    return _is_usable_product(item, require_traceable_source=True)


def _is_usable_reviewed_product(item: Any) -> bool:
    if not _is_usable_product(item, require_traceable_source=False):
        return False
    return _text(item.get("review_status")).casefold() == "approved"


def _json_has_products(path: Path, reviewed: bool = False) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    if isinstance(data, dict):
        data = data.get("products", [])
    if not isinstance(data, list) or not data:
        return False
    validator = _is_usable_reviewed_product if reviewed else _is_usable_crawler_product
    return any(validator(item) for item in data)


def _read_json_if_exists(path: str | Path | None) -> Any:
    if path is None:
        return None
    json_path = Path(path)
    if not json_path.exists() or json_path.stat().st_size == 0:
        return None
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _json_item_count(data: Any, key: str = "products") -> int:
    if isinstance(data, dict):
        data = data.get(key, [])
    if isinstance(data, list):
        return len([item for item in data if isinstance(item, dict)])
    return 0


def _data_source_label(products_json_path: Path) -> str:
    source_name = products_json_path.name
    if source_name == DEFAULT_REVIEWED_PRODUCTS_PATH.name:
        return "reviewed_products.json（已复核 approved 商品）"
    if source_name == DEFAULT_CRAWLER_PRODUCTS_PATH.name:
        return "crawler_products.json（公开 URL 采集候选商品）"
    if source_name == DEFAULT_SAMPLE_PRODUCTS_PATH.name:
        return "sample_products.json（本地样例商品兜底）"
    return source_name


def _build_review_status_metadata(
    reviewed_products_path: str | Path | None,
    review_report_path: str | Path | None,
) -> dict[str, Any]:
    reviewed_path = Path(reviewed_products_path) if reviewed_products_path is not None else None
    report_path = Path(review_report_path) if review_report_path is not None else None
    reviewed_data = _read_json_if_exists(reviewed_path)
    report = _read_json_if_exists(report_path)

    if not isinstance(report, dict):
        report = {}

    reviewed_products_count = _json_item_count(reviewed_data)
    if not reviewed_products_count:
        reviewed_products_count = int(report.get("reviewed_products_count") or 0)

    unmatched_review_items = report.get("unmatched_review_items", [])
    unmatched_review_items_count = len(unmatched_review_items) if isinstance(unmatched_review_items, list) else 0
    unresolved_items = report.get("unresolved_items", [])
    unresolved_items_count = len(unresolved_items) if isinstance(unresolved_items, list) else 0

    has_reviewed_products = reviewed_path is not None and reviewed_path.exists()
    has_review_report = report_path is not None and report_path.exists()
    if not has_reviewed_products and not has_review_report:
        risk_note = "未发现人工复核结果文件，所有候选商品和关键字段仍需人工复核。"
    elif unmatched_review_items_count or unresolved_items_count or int(report.get("needs_more_info_count") or 0):
        risk_note = "已存在人工复核信息，但仍有未匹配或待补充项，需要继续人工复核。"
    else:
        risk_note = "已读取人工复核文件；采购前仍需人工确认候选商品、价格、规格、来源和证据。"

    return {
        "has_reviewed_products": has_reviewed_products,
        "has_review_report": has_review_report,
        "reviewed_products_count": reviewed_products_count,
        "approved_count": int(report.get("approved_count") or 0),
        "rejected_count": int(report.get("rejected_count") or 0),
        "needs_more_info_count": int(report.get("needs_more_info_count") or 0),
        "unmatched_review_items_count": unmatched_review_items_count,
        "risk_note": risk_note,
    }


def _build_delivery_metadata(
    products_json: Path,
    output_root: Path,
    requirements_count: int,
    products_count: int,
    ranked_products_count: int,
    top_products_count: int,
    requirements_path: Path,
    ranked_products_path: Path,
    responses_path: Path,
    output_docx: Path,
    reviewed_products_path: str | Path | None,
    review_report_path: str | Path | None,
    marketplace_search: dict[str, Any] | None = None,
    scoring_csv_path: str | Path | None = None,
) -> dict[str, Any]:
    output_file_index = list(DELIVERY_OUTPUT_FILE_INDEX)
    if scoring_csv_path:
        score_path_text = str(scoring_csv_path)
        if score_path_text not in output_file_index:
            output_file_index.append(score_path_text)
    search = marketplace_search or {}
    return {
        "data_source_priority": DATA_SOURCE_PRIORITY,
        "actual_data_source": _data_source_label(products_json),
        "products_source_path": str(products_json),
        "data_source_note": "系统按 reviewed_products.json、crawler_products.json、sample_products.json 的优先级选择可用商品数据；空文件或无可用商品时继续后退。",
        "requirements_count": requirements_count,
        "products_count": products_count,
        "ranked_products_count": ranked_products_count,
        "top_products_count": top_products_count,
        "output_paths": {
            "requirements_json": str(requirements_path),
            "ranked_products_json": str(ranked_products_path),
            "responses_json": str(responses_path),
            "recommendation_result_docx": str(output_docx),
            "crawler_products_json": str(output_root / DEFAULT_CRAWLER_PRODUCTS_PATH.name),
            "manual_review_items_json": str(output_root / DEFAULT_MANUAL_REVIEW_PATH.name),
            "manual_review_filled_template_json": str(output_root / "manual_review_filled_template.json"),
            "manual_review_validation_report_json": str(output_root / "manual_review_validation_report.json"),
            "reviewed_products_json": str(output_root / DEFAULT_REVIEWED_PRODUCTS_PATH.name),
            "review_report_json": str(output_root / DEFAULT_REVIEW_REPORT_PATH.name),
            "sourcing_score_table_csv": str(scoring_csv_path) if scoring_csv_path else "",
        },
        "output_file_index": output_file_index,
        "review_status": _build_review_status_metadata(reviewed_products_path, review_report_path),
        "marketplace_search": search,
        "sourcing_keywords": search,
        "platform_filter_suggestions": search.get("filter_suggestions", []) if isinstance(search, dict) else [],
    }


def _select_products_json_path(
    crawler_products_path: str | Path = DEFAULT_CRAWLER_PRODUCTS_PATH,
    fallback_products_path: str | Path = DEFAULT_SAMPLE_PRODUCTS_PATH,
    reviewed_products_path: str | Path | None | object = _REVIEWED_PATH_UNSET,
) -> Path:
    if reviewed_products_path is _REVIEWED_PATH_UNSET:
        use_default_reviewed = (
            Path(crawler_products_path) == DEFAULT_CRAWLER_PRODUCTS_PATH
            and Path(fallback_products_path) == DEFAULT_SAMPLE_PRODUCTS_PATH
        )
        reviewed_path = DEFAULT_REVIEWED_PRODUCTS_PATH if use_default_reviewed else None
    else:
        reviewed_path = Path(reviewed_products_path) if reviewed_products_path is not None else None

    if reviewed_path is not None and _json_has_products(reviewed_path, reviewed=True):
        return reviewed_path

    crawler_path = Path(crawler_products_path)
    if _json_has_products(crawler_path):
        return crawler_path
    return Path(fallback_products_path)


def run_pipeline(
    input_docx_path: str | Path = DEFAULT_WORD_PATH,
    products_json_path: str | Path | None = None,
    output_dir: str | Path = OUTPUT_DIR,
    reviewed_products_path: str | Path | None = DEFAULT_REVIEWED_PRODUCTS_PATH,
    review_report_path: str | Path | None = DEFAULT_REVIEW_REPORT_PATH,
    candidate_products: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_docx = Path(input_docx_path)
    products_json = (
        Path(products_json_path)
        if products_json_path is not None
        else _select_products_json_path(reviewed_products_path=reviewed_products_path)
    )
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    requirements_path = output_root / "requirements.json"
    ranked_products_path = output_root / "ranked_products.json"
    responses_path = output_root / "responses.json"
    output_docx = output_root / "recommendation_result.docx"
    manual_review_path = output_root / DEFAULT_MANUAL_REVIEW_PATH.name

    _require_file(input_docx, "默认 Word 文档")
    if candidate_products is None:
        _require_file(products_json, "候选商品 JSON")

    requirements = parse_requirements(input_docx)
    save_requirements_json(requirements, requirements_path)

    if candidate_products is None:
        products = load_products_json(products_json)
    else:
        products = [_normalize_stage13_2b_candidate(item) for item in candidate_products if isinstance(item, dict)]
    ranked_products = rank_products(products, requirements)
    ranked_products = enrich_ranked_products_with_sourcing_guidance(ranked_products, requirements)
    save_ranked_products_json(ranked_products, ranked_products_path)
    scoring_csv_path = write_scoring_csv(ranked_products, output_root / "sourcing_score_table.csv")

    top_products = select_top_products(ranked_products, top_n=3)
    responses = build_recommendation_responses(requirements, ranked_products, top_n=3)
    save_responses_json(responses, responses_path)

    if not top_products:
        raise ValueError("没有可用 Top 3 候选商品，已停止 Word 写回。")

    marketplace_search = build_marketplace_search_links(requirements)
    delivery_metadata = _build_delivery_metadata(
        products_json=products_json,
        output_root=output_root,
        requirements_count=len(requirements),
        products_count=len(products),
        ranked_products_count=len(ranked_products),
        top_products_count=len(top_products),
        requirements_path=requirements_path,
        ranked_products_path=ranked_products_path,
        responses_path=responses_path,
        output_docx=output_docx,
        reviewed_products_path=reviewed_products_path,
        review_report_path=review_report_path,
        marketplace_search=marketplace_search,
        scoring_csv_path=scoring_csv_path,
    )
    write_responses(input_docx, responses, output_docx, summary_products=top_products, delivery_metadata=delivery_metadata)

    result = {
        "requirements_count": len(requirements),
        "products_count": len(products),
        "ranked_products_count": len(ranked_products),
        "top_products_count": len(top_products),
        "responses_count": len(responses),
        "top_products": top_products,
        "requirements_path": str(requirements_path),
        "ranked_products_path": str(ranked_products_path),
        "responses_path": str(responses_path),
        "output_docx_path": str(output_docx),
        "products_source_path": str(products_json),
        "marketplace_search": marketplace_search,
        "sourcing_keywords": marketplace_search,
        "platform_filter_suggestions": marketplace_search.get("filter_suggestions", []),
        "scoring_csv_path": str(scoring_csv_path),
    }
    if manual_review_path.exists():
        result["manual_review_path"] = str(manual_review_path)
    if reviewed_products_path is not None and Path(reviewed_products_path).exists():
        result["reviewed_products_path"] = str(reviewed_products_path)
    if review_report_path is not None and Path(review_report_path).exists():
        result["review_report_path"] = str(review_report_path)
    return result


def run_stage13_2b_delivery(
    input_docx_path: str | Path,
    candidate_file_path: str | Path,
    output_dir: str | Path = OUTPUT_DIR / "stage13_2b_mvp",
) -> dict[str, Any]:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    candidate_products = load_candidate_products_file(candidate_file_path)
    if not candidate_products:
        raise ValueError("候选商品文件未读取到可用商品。")

    imported_products_path = save_candidate_products_json(
        candidate_products,
        output_root / "candidate_products_imported.json",
    )
    result = run_pipeline(
        input_docx_path=input_docx_path,
        products_json_path=imported_products_path,
        output_dir=output_root,
        reviewed_products_path=None,
        review_report_path=None,
        candidate_products=candidate_products,
    )
    result["candidate_file_path"] = str(candidate_file_path)
    result["imported_candidate_products_path"] = str(imported_products_path)
    return result


def run_stage14_v2a_delivery(
    input_docx_path: str | Path,
    candidate_file_path: str | Path,
    output_dir: str | Path = OUTPUT_DIR / "stage14_v2a_mvp",
) -> dict[str, Any]:
    return run_stage13_2b_delivery(input_docx_path, candidate_file_path, output_dir=output_dir)


def run_stage15_smart_sourcing_delivery(
    input_docx_path: str | Path,
    candidate_file_path: str | Path,
    output_dir: str | Path = OUTPUT_DIR / "stage15_v2a_plus",
) -> dict[str, Any]:
    return run_stage13_2b_delivery(input_docx_path, candidate_file_path, output_dir=output_dir)


def main() -> int:
    try:
        result = run_pipeline()
    except Exception as exc:
        print(f"端到端流程失败：{exc}")
        return 1

    print("端到端流程完成。")
    print(f"requirements 数量：{result['requirements_count']}")
    print(f"候选商品数量：{result['products_count']}")
    print(f"排序商品数量：{result['ranked_products_count']}")
    print(f"Top 候选商品数量：{result['top_products_count']}")
    print(f"responses 数量：{result['responses_count']}")
    print(f"requirements.json：{result['requirements_path']}")
    print(f"ranked_products.json：{result['ranked_products_path']}")
    print(f"responses.json：{result['responses_path']}")
    print(f"Word 输出：{result['output_docx_path']}")
    print(f"候选商品来源：{result['products_source_path']}")
    if "scoring_csv_path" in result:
        print(f"评分表 CSV：{result['scoring_csv_path']}")
    if "manual_review_path" in result:
        print(f"人工复核清单：{result['manual_review_path']}")
    if "reviewed_products_path" in result:
        print(f"已复核商品：{result['reviewed_products_path']}")
    if "review_report_path" in result:
        print(f"复核报告：{result['review_report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
