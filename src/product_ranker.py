import json
import re
from pathlib import Path
from typing import Any

from src.product_loader import load_products


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS_PATH = BASE_DIR / "data" / "products.json"
DEFAULT_REQUIREMENTS_PATH = BASE_DIR / "outputs" / "requirements.json"
DEFAULT_RANKED_PRODUCTS_PATH = BASE_DIR / "outputs" / "ranked_products.json"

TITLE_KEYWORD_SCORES = {
    "办公屏风": 10,
    "屏风": 5,
    "工位": 5,
    "隔断": 5,
    "办公桌": 4,
    "卡位": 3,
    "卡座": 3,
}
MATERIAL_KEYWORDS = ["钢制", "钢架", "钢木", "颗粒板", "板材", "玻璃", "框架", "金属", "铝合金", "不锈钢"]
SERVICE_KEYWORDS = ["配送", "送货", "安装", "售后", "质保"]
UNRELATED_TITLE_KEYWORDS = ["电热水壶", "水壶", "烧水", "家用"]
CATEGORY_KEYWORDS = ["办公家具", "办公屏风", "屏风", "工位", "隔断", "办公桌", "卡位", "卡座"]
COLOR_KEYWORDS = ["灰白色", "灰白", "白色", "灰色", "银色", "黑色", "木色"]
STYLE_KEYWORDS = ["普通型", "教学型", "简约", "现代", "开放办公", "办公", "工程采购"]
PRODUCT_TEXT_FIELDS = [
    "title",
    "brand",
    "category",
    "material",
    "color",
    "dimensions",
    "style",
    "specs_text",
    "service_text",
    "raw_text",
    "notes",
]
COMPLETE_FIELDS = ["title", "specs_text", "service_text", "raw_text", "url", "price", "material", "dimensions"]


def _normalize_space(text: str) -> str:
    return " ".join(text.split())


def collect_requirement_text(requirements: Any) -> str:
    values: list[str] = []

    def collect(value: Any) -> None:
        if value is None:
            return
        if isinstance(value, str):
            if value.strip():
                values.append(value.strip())
            return
        if isinstance(value, dict):
            priority_keys = ["name", "required_value", "raw_text", "text", "value", "unit", "index", "response_value"]
            visited: set[str] = set()
            for key in priority_keys:
                if key in value:
                    visited.add(key)
                    collect(value[key])
            for key, nested_value in value.items():
                if key not in visited:
                    collect(nested_value)
            return
        if isinstance(value, (list, tuple)):
            for item in value:
                collect(item)
            return
        if isinstance(value, (int, float)):
            values.append(str(value))

    collect(requirements)
    return _normalize_space(" ".join(values))


def _product_text(product: dict[str, Any]) -> str:
    return _normalize_space(" ".join(str(product.get(field, "") or "") for field in PRODUCT_TEXT_FIELDS))


def _looks_like_product(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    product_keys = {"title", "product_id", "price", "specs_text", "service_text", "raw_text", "category", "platform", "source"}
    requirement_keys = {"required_value", "response_value", "unit", "index"}
    return bool(product_keys.intersection(value)) and not bool(requirement_keys.intersection(value))


def _normalize_score_args(requirements: Any, product: Any) -> tuple[Any, Any]:
    if _looks_like_product(requirements) and not _looks_like_product(product):
        return product, requirements
    return requirements, product


def _extract_numbers(text: str) -> list[str]:
    numbers = re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", text)
    unique_numbers: list[str] = []
    for number in numbers:
        if len(number.replace(".", "")) < 3:
            continue
        if number not in unique_numbers:
            unique_numbers.append(number)
    return unique_numbers


def _extract_size_numbers(requirements: Any, requirement_text: str) -> list[str]:
    size_text_parts: list[str] = []

    if isinstance(requirements, list):
        for item in requirements:
            if not isinstance(item, dict):
                continue
            item_text = collect_requirement_text(item)
            if any(keyword in item_text for keyword in ["尺寸", "长", "宽", "高"]):
                size_text_parts.append(item_text)
    elif isinstance(requirements, dict):
        item_text = collect_requirement_text(requirements)
        if any(keyword in item_text for keyword in ["尺寸", "长", "宽", "高"]):
            size_text_parts.append(item_text)

    size_numbers = _extract_numbers(" ".join(size_text_parts))
    return size_numbers or _extract_numbers(requirement_text)


def _contains_number(text: str, number: str) -> bool:
    pattern = rf"(?<![\d.]){re.escape(number)}(?![\d.])"
    return re.search(pattern, text) is not None


def _clamp_score(score: int) -> int:
    return max(0, min(100, score))


def _detail(score: int, matched: list[str] | None = None, note: str = "") -> dict[str, Any]:
    return {"score": score, "matched": matched or [], "note": note}


def _matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword in text]


def explain_score(requirements: Any, product: dict[str, Any], score_detail: dict[str, Any]) -> dict[str, list[str] | str]:
    title = str(product.get("title", "") or "")
    reasons: list[str] = []
    risks: list[str] = []

    for key in [
        "category",
        "title",
        "dimensions",
        "material",
        "color",
        "style",
        "service",
        "completeness",
        "price",
    ]:
        item = score_detail.get(key, {})
        score = item.get("score", 0)
        note = item.get("note", "")
        if score and note:
            reasons.append(note)

    penalty_detail = score_detail.get("penalty", {})
    risks.extend(penalty_detail.get("risks", []))

    if not reasons:
        reasons.append(f"商品《{title}》未命中主要规则，仅可作为低置信度候选。")

    return {"reasons": reasons, "risks": risks, "reason": "；".join(reasons)}


def score_product(requirements: Any, product: dict[str, Any]) -> dict[str, Any]:
    requirements, product = _normalize_score_args(requirements, product)
    if not isinstance(product, dict):
        raise ValueError("商品数据必须是对象。")

    risks: list[str] = []
    score = 0
    score_detail: dict[str, Any] = {}

    requirement_text = collect_requirement_text(requirements)
    product_text = _product_text(product)
    category_text = _normalize_space(
        " ".join(str(product.get(field, "") or "") for field in ["title", "category", "style", "specs_text", "material"])
    )
    style_text = _normalize_space(
        " ".join(str(product.get(field, "") or "") for field in ["title", "category", "style", "specs_text"])
    )
    title = str(product.get("title", "") or "")

    matched_categories = _matched_keywords(category_text, CATEGORY_KEYWORDS)
    if matched_categories:
        category_score = min(12, len(matched_categories) * 4)
        score += category_score
        score_detail["category"] = _detail(
            category_score,
            matched_categories,
            f"类目或商品文本命中 {', '.join(matched_categories)}，类目匹配度加 {category_score} 分。",
        )
    else:
        score_detail["category"] = _detail(0)

    title_score = min(25, sum(points for keyword, points in TITLE_KEYWORD_SCORES.items() if keyword in title))
    if title_score:
        score += title_score
        matched_title_keywords = [keyword for keyword in TITLE_KEYWORD_SCORES if keyword in title]
        score_detail["title"] = _detail(
            title_score,
            matched_title_keywords,
            f"标题相关关键词命中 {', '.join(matched_title_keywords)}，标题相关度加 {title_score} 分。",
        )
    else:
        score_detail["title"] = _detail(0)

    size_numbers = _extract_size_numbers(requirements, requirement_text)
    matched_size_numbers = [number for number in size_numbers if _contains_number(product_text, number)]
    if matched_size_numbers:
        size_score = min(20, len(matched_size_numbers) * 10)
        score += size_score
        score_detail["dimensions"] = _detail(
            size_score,
            matched_size_numbers,
            f"尺寸数字命中 {', '.join(matched_size_numbers)}，尺寸匹配度加 {size_score} 分。",
        )
    else:
        score_detail["dimensions"] = _detail(0)

    matched_materials = [keyword for keyword in MATERIAL_KEYWORDS if keyword in product_text]
    if matched_materials:
        material_score = min(15, len(matched_materials) * 3)
        score += material_score
        score_detail["material"] = _detail(
            material_score,
            matched_materials,
            f"材质关键词命中 {', '.join(matched_materials)}，材质匹配度加 {material_score} 分。",
        )
    else:
        score_detail["material"] = _detail(0)

    required_colors = _matched_keywords(requirement_text, COLOR_KEYWORDS)
    product_colors = _matched_keywords(product_text, COLOR_KEYWORDS)
    matched_colors = [color for color in product_colors if not required_colors or color in required_colors]
    if matched_colors:
        color_score = 8
        score += color_score
        score_detail["color"] = _detail(
            color_score,
            matched_colors,
            f"颜色关键词命中 {', '.join(matched_colors)}，颜色匹配度加 {color_score} 分。",
        )
    else:
        score_detail["color"] = _detail(0)

    matched_styles = [keyword for keyword in STYLE_KEYWORDS if keyword in style_text and keyword in requirement_text]
    if matched_styles:
        style_score = min(5, len(matched_styles) * 3)
        score += style_score
        score_detail["style"] = _detail(
            style_score,
            matched_styles,
            f"风格或场景关键词命中 {', '.join(matched_styles)}，风格匹配度加 {style_score} 分。",
        )
    else:
        score_detail["style"] = _detail(0)

    service_text = str(product.get("service_text", "") or "")
    matched_services = [keyword for keyword in SERVICE_KEYWORDS if keyword in service_text]
    if matched_services:
        service_score = min(10, len(matched_services) * 3)
        score += service_score
        score_detail["service"] = _detail(
            service_score,
            matched_services,
            f"服务关键词命中 {', '.join(matched_services)}，服务匹配度加 {service_score} 分。",
        )
    else:
        score_detail["service"] = _detail(0)

    complete_count = sum(1 for field in COMPLETE_FIELDS if product.get(field) not in (None, ""))
    completeness_score = min(10, complete_count * 2)
    if completeness_score:
        score += completeness_score
        score_detail["completeness"] = _detail(
            completeness_score,
            [f"{complete_count}/{len(COMPLETE_FIELDS)}"],
            f"关键字段完整度为 {complete_count}/{len(COMPLETE_FIELDS)}，参数完整度加 {completeness_score} 分。",
        )
    else:
        score_detail["completeness"] = _detail(0)

    price = product.get("price")
    price_is_number = isinstance(price, (int, float)) and not isinstance(price, bool)
    if price_is_number:
        if 300 <= float(price) <= 5000:
            price_score = 10
            price_note = "价格处于常见办公家具区间，价格合理性加 10 分。"
        elif 100 <= float(price) < 300 or 5000 < float(price) <= 10000:
            price_score = 5
            price_note = "价格为数字但处于边缘区间，价格合理性加 5 分。"
        else:
            price_score = 2
            price_note = "价格为数字但明显偏离常见办公家具区间，价格合理性加 2 分。"
        score += price_score
        score_detail["price"] = _detail(price_score, [str(price)], price_note)
    else:
        score_detail["price"] = _detail(0)

    penalty = 0
    if not matched_categories:
        risks.append("类目或商品文本未明确命中办公家具、屏风、工位等关键词，需人工确认类目。")
        penalty += 3
    if title_score < 8:
        risks.append("标题相关度较弱，需人工确认是否属于办公屏风工位。")
        penalty += 3
    if not matched_size_numbers:
        risks.append("商品文本未明确命中采购尺寸数字，需人工复核尺寸。")
        penalty += 2
    if not matched_materials:
        risks.append("商品文本未明确命中阶段 3 材质关键词，需人工复核材质。")
        penalty += 2
    if required_colors and not matched_colors:
        risks.append("商品文本未明确命中采购颜色要求，需人工复核颜色。")
        penalty += 1
    if not matched_services:
        risks.append("服务文本未明确命中配送、安装、售后或质保关键词，需人工复核服务。")
        penalty += 1
    if not price_is_number:
        risks.append("价格缺失或不是数字，需人工复核价格。")
        penalty += 2
    if any(keyword in title for keyword in UNRELATED_TITLE_KEYWORDS):
        risks.append("标题出现明显无关商品关键词，需排除非办公屏风类商品。")
        penalty += 10

    applied_penalty = min(15, penalty)
    score_detail["penalty"] = {"score": -applied_penalty, "risks": risks}
    score = _clamp_score(score - applied_penalty)
    explanation = explain_score(requirements, product, score_detail)

    ranked_product = dict(product)
    ranked_product["score"] = score
    ranked_product["total_score"] = score
    ranked_product["score_detail"] = score_detail
    ranked_product["reasons"] = list(explanation["reasons"])
    ranked_product["risks"] = list(explanation["risks"])
    ranked_product["reason"] = str(explanation["reason"])
    return ranked_product


def rank_products(products: list[dict[str, Any]], requirements: Any) -> list[dict[str, Any]]:
    ranked_products = [score_product(requirements, product) for product in products if isinstance(product, dict)]
    return sorted(ranked_products, key=lambda item: item["score"], reverse=True)


def save_ranked_products_json(ranked_products: list[dict[str, Any]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(ranked_products, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_requirements(path: Path) -> Any:
    if not path.exists():
        print(f"未找到 requirements JSON：{path}")
        print("请先在 Streamlit 页面上传 Word 并完成解析，生成 outputs/requirements.json。")
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"requirements JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc


def main() -> int:
    try:
        requirements = _load_requirements(DEFAULT_REQUIREMENTS_PATH)
        if requirements is None:
            return 1

        products = load_products(DEFAULT_PRODUCTS_PATH)
        ranked_products = rank_products(products, requirements)
        save_ranked_products_json(ranked_products, DEFAULT_RANKED_PRODUCTS_PATH)

        scores = [product["score"] for product in ranked_products]
        first_title = ranked_products[0]["title"] if ranked_products else ""
        highest_score = max(scores) if scores else 0
        lowest_score = min(scores) if scores else 0

        print(f"商品总数：{len(products)}")
        print(f"排序商品总数：{len(ranked_products)}")
        print(f"第一名商品标题：{first_title}")
        print(f"最高分：{highest_score}")
        print(f"最低分：{lowest_score}")
        print(f"ranked_products.json 保存路径：{DEFAULT_RANKED_PRODUCTS_PATH}")
        return 0
    except Exception as exc:
        print(f"商品排序失败：{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
