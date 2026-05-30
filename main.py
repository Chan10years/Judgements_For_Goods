from pathlib import Path
from typing import Any
import json

from src.doc_parser import parse_requirements, save_requirements_json
from src.doc_writer import write_responses
from src.product_loader import load_products_json
from src.product_ranker import rank_products, save_ranked_products_json
from src.response_builder import build_recommendation_responses, save_responses_json, select_top_products


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
_REVIEWED_PATH_UNSET = object()


def _require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{label}不存在：{path}")


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


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
    _require_file(products_json, "候选商品 JSON")

    requirements = parse_requirements(input_docx)
    save_requirements_json(requirements, requirements_path)

    products = load_products_json(products_json)
    ranked_products = rank_products(products, requirements)
    save_ranked_products_json(ranked_products, ranked_products_path)

    top_products = select_top_products(ranked_products, top_n=3)
    responses = build_recommendation_responses(requirements, ranked_products, top_n=3)
    save_responses_json(responses, responses_path)

    if not top_products:
        raise ValueError("没有可用 Top 3 候选商品，已停止 Word 写回。")

    write_responses(input_docx, responses, output_docx, summary_products=top_products)

    result = {
        "requirements_count": len(requirements),
        "products_count": len(products),
        "ranked_products_count": len(ranked_products),
        "top_products_count": len(top_products),
        "responses_count": len(responses),
        "requirements_path": str(requirements_path),
        "ranked_products_path": str(ranked_products_path),
        "responses_path": str(responses_path),
        "output_docx_path": str(output_docx),
        "products_source_path": str(products_json),
    }
    if manual_review_path.exists():
        result["manual_review_path"] = str(manual_review_path)
    if reviewed_products_path is not None and Path(reviewed_products_path).exists():
        result["reviewed_products_path"] = str(reviewed_products_path)
    if review_report_path is not None and Path(review_report_path).exists():
        result["review_report_path"] = str(review_report_path)
    return result


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
    if "manual_review_path" in result:
        print(f"人工复核清单：{result['manual_review_path']}")
    if "reviewed_products_path" in result:
        print(f"已复核商品：{result['reviewed_products_path']}")
    if "review_report_path" in result:
        print(f"复核报告：{result['review_report_path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
