import json
import re
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_REQUIREMENTS_PATH = BASE_DIR / "outputs" / "requirements.json"
DEFAULT_RANKED_PRODUCTS_PATH = BASE_DIR / "outputs" / "ranked_products.json"
DEFAULT_RESPONSES_PATH = BASE_DIR / "outputs" / "responses.json"

UNRELATED_TITLE_KEYWORDS = ["电热水壶", "水壶", "烧水", "家用"]
RELEVANT_TITLE_KEYWORDS = ["办公屏风", "屏风", "工位", "隔断", "办公桌", "卡位", "卡座"]
PRODUCT_TEXT_FIELDS = ["title", "specs_text", "service_text", "raw_text"]


def _normalize_space(text: Any) -> str:
    return " ".join(str(text or "").split())


def _product_text(product: dict[str, Any]) -> str:
    return _normalize_space(" ".join(str(product.get(field, "") or "") for field in PRODUCT_TEXT_FIELDS))


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _contains_number(text: str, number: str) -> bool:
    pattern = rf"(?<![\d.]){re.escape(number)}(?![\d.])"
    return re.search(pattern, text) is not None


def _extract_numbers(text: str) -> list[str]:
    numbers = re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", text)
    unique_numbers: list[str] = []
    for number in numbers:
        if number not in unique_numbers:
            unique_numbers.append(number)
    return unique_numbers


def _evidence_for_keywords(product_text: str, keywords: list[str]) -> list[str]:
    return [keyword for keyword in keywords if keyword and keyword in product_text]


def _review_response(reason: str, title: str) -> tuple[str, str, bool]:
    response_value = f"需人工复核：第一候选商品文本未明确确认{reason}。"
    evidence = f"第一候选商品《{title}》文本未检索到可直接确认该项要求的明确证据。"
    return response_value, evidence, True


def _build_response_value(requirement: dict[str, Any], top_product: dict[str, Any]) -> tuple[str, str, bool]:
    name = _normalize_space(requirement.get("name"))
    required_value = _normalize_space(requirement.get("required_value"))
    title = _normalize_space(top_product.get("title"))
    product_text = _product_text(top_product)

    if "尺寸" in name or any(keyword in required_value for keyword in ["长", "宽", "高"]):
        numbers = [number for number in _extract_numbers(required_value) if len(number.replace(".", "")) >= 3]
        matched_numbers = [number for number in numbers if _contains_number(product_text, number)]
        if numbers and all(number in matched_numbers for number in numbers):
            value = "、".join(matched_numbers)
            return (
                f"响应：第一候选商品文本明确包含尺寸数字 {value}。",
                f"第一候选商品《{title}》商品文本包含：{value}。",
                False,
            )
        return _review_response("尺寸要求", title)

    if "材质" in name:
        matched = _evidence_for_keywords(product_text, ["钢制框架", "钢制", "钢架", "实木颗粒板", "颗粒板", "板材"])
        if matched:
            missing = []
            for keyword in ["Q235", "冷轧钢板", "1.2mm", "700kg/m", "700kg/m³", "防火"]:
                if keyword not in product_text:
                    missing.append(keyword)
            if missing:
                return (
                    f"需人工复核：第一候选商品文本明确包含{', '.join(matched)}；未明确确认{', '.join(missing)}等要求。",
                    f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                    True,
                )
            return (
                f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("主体材质要求", title)

    if "颜色" in name:
        matched = _evidence_for_keywords(product_text, ["灰白色", "白色", "灰色"])
        if matched:
            return (
                f"响应：第一候选商品文本明确包含颜色信息 {', '.join(matched)}。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("主体颜色要求", title)

    if "功能" in name or "定位" in name:
        matched = _evidence_for_keywords(product_text, ["办公工位", "办公", "工位", "办公室"])
        if matched:
            return (
                f"响应：第一候选商品文本明确适用于{', '.join(matched)}场景。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("产品功能定位", title)

    if "安装方式" in name:
        matched = _evidence_for_keywords(product_text, ["两面独立工作位", "独立工作位"])
        if matched:
            return (
                f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("安装方式要求", title)

    if "配送" in name or "安装" in name:
        matched = _evidence_for_keywords(product_text, ["送货至指定地点", "送货", "配送", "现场安装", "安装"])
        if matched:
            missing = []
            if "不额外收费" in required_value and "不额外收费" not in product_text and "免费" not in product_text:
                missing.append("不额外收费")
            if missing:
                return (
                    f"需人工复核：第一候选商品文本明确包含{', '.join(matched)}；未明确确认{', '.join(missing)}。",
                    f"第一候选商品《{title}》服务文本包含：{', '.join(matched)}。",
                    True,
                )
            return (
                f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
                f"第一候选商品《{title}》服务文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("配送及安装要求", title)

    if "屏风主体" in name:
        matched = _evidence_for_keywords(product_text, ["玻璃", "屏风", "隔断屏", "隔断"])
        if "玻璃" in required_value and "玻璃" not in product_text:
            return _review_response("屏风主体材质", title)
        if matched:
            return (
                f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("屏风主体要求", title)

    if "连接结构" in name:
        matched = _evidence_for_keywords(product_text, ["连接件", "无需现场焊接", "焊接"])
        if matched and "无需现场焊接" in matched:
            return (
                f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                False,
            )
        return _review_response("连接结构要求", title)

    if "五金" in name:
        matched = _evidence_for_keywords(product_text, ["304", "不锈钢", "连接件", "铰链", "导轨", "阻尼"])
        if matched:
            return (
                f"需人工复核：第一候选商品文本仅明确包含{', '.join(matched)}；未完整确认五金件全部要求。",
                f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
                True,
            )
        return _review_response("五金件要求", title)

    if "承重" in name:
        return _review_response("承重能力要求", title)

    if "表面质量" in name:
        return _review_response("表面质量要求", title)

    if "环保" in name:
        return _review_response("环保要求", title)

    required_keywords = [keyword for keyword in re.split(r"[，,；;、（）() ]+", required_value) if len(keyword) >= 2]
    matched = _evidence_for_keywords(product_text, required_keywords)
    if matched:
        return (
            f"响应：第一候选商品文本明确包含{', '.join(matched)}。",
            f"第一候选商品《{title}》商品文本包含：{', '.join(matched)}。",
            False,
        )
    return _review_response(name or "该项参数", title)


def select_top_products(ranked_products: list[dict[str, Any]], top_n: int = 3) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []

    for product in ranked_products or []:
        if not isinstance(product, dict):
            continue

        title = _normalize_space(product.get("title"))
        risks_text = _normalize_space("；".join(str(item) for item in product.get("risks", [])))
        score = product.get("score", 0)
        score_number = score if isinstance(score, (int, float)) and not isinstance(score, bool) else 0

        has_unrelated_keyword = _contains_any(title, UNRELATED_TITLE_KEYWORDS)
        has_unrelated_risk = "明显无关" in risks_text or "需排除非办公屏风类商品" in risks_text
        has_relevant_title = _contains_any(title, RELEVANT_TITLE_KEYWORDS)
        if has_unrelated_keyword or has_unrelated_risk or (score_number < 30 and not has_relevant_title):
            continue

        selected.append(product)
        if len(selected) >= top_n:
            break

    return selected


def build_recommendation_responses(
    requirements: list[dict[str, Any]],
    ranked_products: list[dict[str, Any]],
    top_n: int = 3,
) -> list[dict[str, Any]]:
    top_products = select_top_products(ranked_products, top_n=top_n)
    if not top_products:
        return []

    top_product = top_products[0]
    title = _normalize_space(top_product.get("title"))
    responses: list[dict[str, Any]] = []

    for item in requirements or []:
        if not isinstance(item, dict):
            continue
        response_value, evidence, review_required = _build_response_value(item, top_product)
        responses.append(
            {
                "index": _normalize_space(item.get("index")),
                "name": _normalize_space(item.get("name")),
                "unit": _normalize_space(item.get("unit")),
                "required_value": _normalize_space(item.get("required_value")),
                "response_value": response_value,
                "source_product_title": title,
                "evidence": evidence,
                "review_required": review_required,
            }
        )

    return responses


def save_responses_json(responses: list[dict[str, Any]], path: str | Path) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(responses, ensure_ascii=False, indent=2), encoding="utf-8")


def _load_json(path: Path, label: str) -> Any | None:
    if not path.exists():
        print(f"未找到 {label} JSON：{path}")
        return None

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"{label} JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}")
        return None


def main() -> int:
    requirements = _load_json(DEFAULT_REQUIREMENTS_PATH, "requirements")
    ranked_products = _load_json(DEFAULT_RANKED_PRODUCTS_PATH, "ranked_products")
    if requirements is None or ranked_products is None:
        print("请先完成阶段 1 解析和阶段 3 排序，生成 outputs/requirements.json 与 outputs/ranked_products.json。")
        return 1

    top_products = select_top_products(ranked_products)
    responses = build_recommendation_responses(requirements, ranked_products)
    save_responses_json(responses, DEFAULT_RESPONSES_PATH)

    print(f"requirements 数量：{len(requirements) if isinstance(requirements, list) else 0}")
    print(f"Top 候选商品数量：{len(top_products)}")
    print(f"responses 数量：{len(responses)}")
    print(f"responses.json 保存路径：{DEFAULT_RESPONSES_PATH}")
    if not top_products:
        print("没有可用候选商品，未生成可写回 Word 的有效规则响应。")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
