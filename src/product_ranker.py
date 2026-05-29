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
PRODUCT_TEXT_FIELDS = ["title", "specs_text", "service_text", "raw_text"]
COMPLETE_FIELDS = ["specs_text", "service_text", "raw_text", "url", "price"]


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


def score_product(product: dict[str, Any], requirements: Any) -> dict[str, Any]:
    if not isinstance(product, dict):
        raise ValueError("商品数据必须是对象。")

    reasons: list[str] = []
    risks: list[str] = []
    score = 0

    requirement_text = collect_requirement_text(requirements)
    product_text = _product_text(product)
    title = str(product.get("title", "") or "")

    title_score = min(25, sum(points for keyword, points in TITLE_KEYWORD_SCORES.items() if keyword in title))
    if title_score:
        score += title_score
        reasons.append(f"标题相关关键词命中，标题相关度加 {title_score} 分。")

    size_numbers = _extract_size_numbers(requirements, requirement_text)
    matched_size_numbers = [number for number in size_numbers if _contains_number(product_text, number)]
    if matched_size_numbers:
        size_score = min(20, len(matched_size_numbers) * 10)
        score += size_score
        reasons.append(f"尺寸数字命中 {', '.join(matched_size_numbers)}，尺寸匹配度加 {size_score} 分。")

    matched_materials = [keyword for keyword in MATERIAL_KEYWORDS if keyword in product_text]
    if matched_materials:
        material_score = min(15, len(matched_materials) * 3)
        score += material_score
        reasons.append(f"材质关键词命中 {', '.join(matched_materials)}，材质匹配度加 {material_score} 分。")

    service_text = str(product.get("service_text", "") or "")
    matched_services = [keyword for keyword in SERVICE_KEYWORDS if keyword in service_text]
    if matched_services:
        service_score = min(10, len(matched_services) * 3)
        score += service_score
        reasons.append(f"服务关键词命中 {', '.join(matched_services)}，服务匹配度加 {service_score} 分。")

    complete_count = sum(1 for field in COMPLETE_FIELDS if product.get(field) not in (None, ""))
    completeness_score = min(10, complete_count * 2)
    if completeness_score:
        score += completeness_score
        reasons.append(f"关键字段完整度为 {complete_count}/{len(COMPLETE_FIELDS)}，参数完整度加 {completeness_score} 分。")

    price = product.get("price")
    price_is_number = isinstance(price, (int, float)) and not isinstance(price, bool)
    if price_is_number:
        if 300 <= float(price) <= 5000:
            price_score = 10
            reasons.append("价格处于常见办公家具区间，价格合理性加 10 分。")
        elif 100 <= float(price) < 300 or 5000 < float(price) <= 10000:
            price_score = 5
            reasons.append("价格为数字但处于边缘区间，价格合理性加 5 分。")
        else:
            price_score = 2
            reasons.append("价格为数字但明显偏离常见办公家具区间，价格合理性加 2 分。")
        score += price_score

    penalty = 0
    if title_score < 8:
        risks.append("标题相关度较弱，需人工确认是否属于办公屏风工位。")
        penalty += 3
    if not matched_size_numbers:
        risks.append("商品文本未明确命中采购尺寸数字，需人工复核尺寸。")
        penalty += 2
    if not matched_materials:
        risks.append("商品文本未明确命中阶段 3 材质关键词，需人工复核材质。")
        penalty += 2
    if not matched_services:
        risks.append("服务文本未明确命中配送、安装、售后或质保关键词，需人工复核服务。")
        penalty += 1
    if not price_is_number:
        risks.append("价格缺失或不是数字，需人工复核价格。")
        penalty += 2
    if any(keyword in title for keyword in UNRELATED_TITLE_KEYWORDS):
        risks.append("标题出现明显无关商品关键词，需排除非办公屏风类商品。")
        penalty += 5

    score = _clamp_score(score - min(10, penalty))

    ranked_product = dict(product)
    ranked_product["score"] = score
    ranked_product["reasons"] = reasons
    ranked_product["risks"] = risks
    return ranked_product


def rank_products(products: list[dict[str, Any]], requirements: Any) -> list[dict[str, Any]]:
    ranked_products = [score_product(product, requirements) for product in products]
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
