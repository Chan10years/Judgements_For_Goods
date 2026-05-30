from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from src.product_ranker import collect_requirement_text


DIMENSION_PATTERN = re.compile(
    r"\d+(?:\.\d+)?\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?(?:\s*(?:x|X|×|\*)\s*\d+(?:\.\d+)?)?\s*(?:mm|毫米|cm|厘米)?"
)
URL_PATTERN = re.compile(r"https?://[^\s,，;；。]+", re.IGNORECASE)
PRICE_PATTERN = re.compile(
    r"(?:价格|价|报价|到手价|￥|¥)\s*(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)\s*(?:元|块)"
)

SEARCH_KEYWORD_HINTS = ["办公屏风", "屏风", "工位", "隔断", "办公桌", "卡位", "卡座"]
MATERIAL_HINTS = [
    "钢制框架",
    "冷轧钢板",
    "实木颗粒板",
    "颗粒板",
    "钢制",
    "钢架",
    "钢木",
    "玻璃",
    "铝合金",
    "不锈钢",
    "板材",
]
COLOR_HINTS = ["灰白色", "灰白", "白色", "灰色", "银色", "黑色", "木色", "原木色"]
INSTALLATION_HINTS = [
    "配送安装",
    "现场安装",
    "上门安装",
    "包安装",
    "支持安装",
    "安装",
    "送货",
    "配送",
]
UNRELATED_EXCLUDE_TERMS = ["家用", "二手", "水壶", "单人小桌"]
UNRELATED_TITLE_KEYWORDS = ["电热水壶", "水壶", "烧水", "家用"]

PENDING_FIELD_LABELS = {
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

SCORING_TABLE_HEADERS = [
    "排名",
    "商品名称",
    "平台",
    "价格",
    "尺寸",
    "材质",
    "安装服务",
    "商品链接",
    "图片链接",
    "匹配分数",
    "命中指标",
    "待复核字段",
    "风险提示",
    "人工确认问题",
    "推荐等级",
]


def _text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_text(*values: Any) -> str:
    for value in values:
        text = _text(value)
        if text:
            return text
    return ""


def _unique_text(items: list[str]) -> list[str]:
    return list(dict.fromkeys(_text(item) for item in items if _text(item)))


def _read_text_with_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="gbk")


def _normalize_dimension(value: str) -> str:
    text = _text(value)
    text = re.sub(r"\s*(?:×|\*)\s*", "x", text)
    text = re.sub(r"\s*[xX]\s*", "x", text)
    return text


def _extract_dimension(text: str) -> str:
    match = DIMENSION_PATTERN.search(text)
    return _normalize_dimension(match.group(0)) if match else ""


def _strip_urls(text: str) -> str:
    return _text(URL_PATTERN.sub(" ", text))


def _detect_platform(url: str = "", text: str = "") -> str:
    combined = f"{url} {text}".lower()
    original = f"{url} {text}"
    if "jd.com" in combined or "jingdong" in combined or "京东" in original:
        return "京东"
    if "tmall.com" in combined or "天猫" in original:
        return "天猫"
    if "taobao.com" in combined or "淘宝" in original:
        return "淘宝"
    return "客户候选"


def _extract_price_from_text(text: str) -> int | float | None:
    without_urls = _strip_urls(text)
    for match in PRICE_PATTERN.finditer(without_urls):
        value = match.group(1) or match.group(2)
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number <= 0 or number > 1_000_000:
            continue
        return int(number) if number.is_integer() else number
    return None


def _matched_hints(text: str, hints: list[str]) -> list[str]:
    return _unique_text([hint for hint in hints if hint in text])


def _extract_title_from_line(line_text: str, platform: str) -> tuple[str, bool]:
    text_without_url = _strip_urls(line_text)
    text_without_dimension = DIMENSION_PATTERN.sub(" ", text_without_url)
    text_without_price = PRICE_PATTERN.sub(" ", text_without_dimension)
    for keyword in MATERIAL_HINTS + INSTALLATION_HINTS + COLOR_HINTS:
        text_without_price = text_without_price.replace(keyword, " ")
    text_without_price = re.sub(r"(^|\s)(淘宝|天猫|京东|平台|商品|支持|可选)(\s|$)", " ", text_without_price)
    title = _text(text_without_price.strip(" ,-，;；|。"))
    if title:
        return title[:120], False
    return f"待人工复核候选商品（{platform}链接）", True


def _pending_fields_for_candidate(candidate: dict[str, Any]) -> list[str]:
    pending = list(candidate.get("missing_fields") or [])
    checks = {
        "title": "" if candidate.get("title_is_placeholder") else candidate.get("title"),
        "platform": candidate.get("platform"),
        "price": candidate.get("price"),
        "url": candidate.get("url"),
        "dimensions": candidate.get("dimensions"),
        "material": candidate.get("material"),
        "installation_service": _first_text(candidate.get("installation_service"), candidate.get("service_text")),
        "image_url": candidate.get("image_url"),
        "evidence_text": _first_text(candidate.get("evidence_text"), candidate.get("evidence")),
    }
    for field, value in checks.items():
        if value is None or (isinstance(value, str) and not _text(value)):
            pending.append(field)
    return _unique_text(pending)


def _candidate_from_line(line: str, url: str, line_number: int) -> dict[str, Any]:
    platform = _detect_platform(url, line)
    title, title_is_placeholder = _extract_title_from_line(line, platform)
    raw_without_url = _strip_urls(line)
    dimensions = _extract_dimension(line)
    material = "，".join(_matched_hints(line, MATERIAL_HINTS))
    color = "，".join(_matched_hints(line, COLOR_HINTS))
    installation_service = "，".join(_matched_hints(line, INSTALLATION_HINTS))
    evidence_text = f"客户在候选链接/文本第 {line_number} 行主动提供：{line}"

    candidate = {
        "title": title,
        "platform": platform,
        "price": _extract_price_from_text(line),
        "url": url,
        "shop": "",
        "source": "客户候选链接/文本",
        "dimensions": dimensions,
        "material": material,
        "color": color,
        "installation_service": installation_service,
        "image_url": "",
        "specs_text": raw_without_url,
        "service_text": installation_service,
        "evidence_text": evidence_text,
        "evidence": evidence_text,
        "raw_text": raw_without_url,
        "adapter_source_type": "manual_mixed_text",
        "adapter_source_label": "客户候选链接/文本",
        "manual_review_required": True,
        "title_is_placeholder": title_is_placeholder,
    }
    candidate["missing_fields"] = _pending_fields_for_candidate(candidate)
    if candidate["missing_fields"]:
        labels = [PENDING_FIELD_LABELS.get(field, field) for field in candidate["missing_fields"]]
        candidate["notes"] = "待人工复核字段：" + "、".join(labels)
    return candidate


def parse_candidate_mixed_text(text: str) -> list[dict[str, Any]]:
    """Parse only customer-provided pasted text; this function never fetches platform pages."""
    products: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(str(text or "").splitlines(), start=1):
        line = _text(raw_line)
        if not line or line.startswith("#"):
            continue
        urls = URL_PATTERN.findall(line)
        if not urls:
            continue
        for url in urls:
            products.append(_candidate_from_line(line, url, line_number))
    return products


def load_candidate_mixed_text_file(path: str | Path) -> list[dict[str, Any]]:
    candidate_path = Path(path)
    if not candidate_path.exists():
        raise FileNotFoundError(f"候选链接/文本清单不存在：{candidate_path}")
    products = parse_candidate_mixed_text(_read_text_with_fallback(candidate_path))
    if not products:
        raise ValueError("候选链接/文本清单未发现 http 或 https 链接。")
    return products


def _requirement_dimension_and_number(requirements: Any, requirement_text: str) -> tuple[str, str]:
    dimension = _extract_dimension(requirement_text)
    if dimension:
        first_number = re.findall(r"\d+(?:\.\d+)?", dimension)
        return dimension, first_number[0] if first_number else ""
    numbers = re.findall(r"(?<![\d.])\d{3,}(?:\.\d+)?(?![\d.])", requirement_text)
    return "", numbers[0] if numbers else ""


def _base_keyword(requirement_text: str) -> str:
    if "屏风" in requirement_text and "工位" in requirement_text:
        return "办公屏风工位"
    if "屏风" in requirement_text and "办公桌" in requirement_text:
        return "办公桌屏风组合"
    if "屏风" in requirement_text:
        return "办公屏风"
    matched = [keyword for keyword in SEARCH_KEYWORD_HINTS if keyword in requirement_text]
    return matched[0] if matched else "办公屏风工位"


def generate_sourcing_keywords(requirements: Any, default_keyword: str = "办公屏风 工位") -> dict[str, Any]:
    requirement_text = collect_requirement_text(requirements)
    base = _base_keyword(requirement_text) if requirement_text else default_keyword
    dimension, first_size_number = _requirement_dimension_and_number(requirements, requirement_text)
    material_terms = _matched_hints(requirement_text, MATERIAL_HINTS)
    service_terms = ["安装"] if any(keyword in requirement_text for keyword in ["安装", "配送", "送货"]) else []

    precise_parts = [base, dimension, material_terms[0] if material_terms else "", service_terms[0] if service_terms else ""]
    precise_term = " ".join(part for part in precise_parts if _text(part)) or default_keyword
    relaxed_term = " ".join(part for part in ["办公桌屏风组合", first_size_number or dimension] if _text(part))
    alternative_term = "职员工位 屏风隔断 办公桌"

    encoded = quote(precise_term)
    keywords = {
        "precise_terms": _unique_text([precise_term]),
        "relaxed_terms": _unique_text([relaxed_term or default_keyword]),
        "alternative_terms": _unique_text([alternative_term, "办公卡位 屏风桌"]),
        "excluded_terms": list(UNRELATED_EXCLUDE_TERMS),
        "taobao_keyword": precise_term,
        "jd_keyword": precise_term,
        "taobao_search_url": f"https://s.taobao.com/search?q={encoded}",
        "jd_search_url": f"https://search.jd.com/Search?keyword={encoded}&enc=utf-8",
        "notice": (
            "当前 V2-A+ 提供智能寻源辅助入口。客户在自己的浏览器中正常登录并人工确认候选商品后，"
            "通过候选商品文件或候选链接/文本清单导入系统，再进入自动筛选排序和 Word 输出流程。"
            "本系统不强抓淘宝/京东搜索页，不写入账号密码或 Cookie，不规避验证码和风控；"
            "淘宝/京东授权 API、合规第三方商品数据和更自动化的数据接入属于后续 V2-B。"
        ),
    }
    keywords["filter_suggestions"] = generate_platform_filter_suggestions(requirements)
    return keywords


def build_marketplace_search_links(requirements: Any = None, default_keyword: str = "办公屏风 工位") -> dict[str, Any]:
    return generate_sourcing_keywords(requirements, default_keyword=default_keyword)


def generate_platform_filter_suggestions(requirements: Any) -> list[dict[str, str]]:
    requirement_text = collect_requirement_text(requirements)
    dimension = _extract_dimension(requirement_text)
    material_terms = _matched_hints(requirement_text, MATERIAL_HINTS)
    service_required = any(keyword in requirement_text for keyword in ["配送", "送货", "安装"])
    price_note = (
        "采购指标未识别到明确预算，不自动给定确认价格；建议按预算人工设置上下限，并逐项确认是否含运费、安装费和税费。"
    )
    if "预算" in requirement_text or "价格" in requirement_text:
        price_note = "按采购预算设置价格筛选上下限，平台展示价仅作为采购辅助线索，需人工确认含税、运费和安装费口径。"

    suggestions = [
        ("价格区间", price_note),
        ("店铺类型", "优先查看企业店、旗舰店、工厂店或可提供批量采购服务的店铺，但仍需人工核验店铺资质和页面证据。"),
        ("发票", "筛选或询问是否可开具合规发票，并记录发票类型、税点和开票主体作为采购辅助证据。"),
        (
            "配送安装",
            "优先保留明确写有配送、送货或安装服务的候选；"
            + ("本采购指标包含配送/安装要求，需特别确认是否另收费。" if service_required else "未确认前不要写成已包含服务。"),
        ),
        ("本地/同城/批量采购", "需要现场安装或交付时，建议关注本地、同城、批量采购、工程采购等服务标签，并人工确认覆盖区域。"),
        (
            "规格完整性",
            "优先保留规格完整候选；"
            + (f"重点核对尺寸 {dimension}。" if dimension else "尺寸、长宽高和屏风高度缺失时需补充。")
            + (" 材质需核对：" + "、".join(material_terms) + "。" if material_terms else " 材质字段缺失时需补充。"),
        ),
        ("售后", "记录质保、退换货、安装后维护和响应时效；没有页面或客服证据时保持待复核。"),
        ("截图或页面证据", "保留商品页截图、链接、关键规格和服务说明截图；系统只把这些作为采购辅助证据，不替代人工确认。"),
    ]
    return [{"category": category, "suggestion": suggestion} for category, suggestion in suggestions]


def _field_labels(fields: list[str]) -> list[str]:
    return [PENDING_FIELD_LABELS.get(field, field) for field in _unique_text(fields)]


def pending_review_fields(product: dict[str, Any]) -> list[str]:
    fields = list(product.get("missing_fields") or [])
    checks = {
        "title": "" if product.get("title_is_placeholder") else product.get("title"),
        "price": product.get("price"),
        "dimensions": product.get("dimensions"),
        "material": product.get("material"),
        "installation_service": _first_text(product.get("installation_service"), product.get("service_text")),
        "url": product.get("url"),
        "image_url": product.get("image_url"),
        "evidence_text": _first_text(product.get("evidence_text"), product.get("evidence")),
    }
    for field, value in checks.items():
        if value is None or (isinstance(value, str) and not _text(value)):
            fields.append(field)
    return _unique_text(fields)


def build_manual_confirmation_questions(product: dict[str, Any], requirements: Any | None = None) -> list[str]:
    pending_labels = _field_labels(pending_review_fields(product))
    pending_text = "、".join(pending_labels) if pending_labels else "暂无系统识别的缺失字段"
    return [
        "价格是否已人工确认，是否包含运费、安装费和税费？",
        "尺寸是否满足采购指标，长宽高、屏风高度和单位是否一致？",
        "材质是否明确，是否有页面文本、客服记录或截图证据？",
        "是否支持配送和安装，服务范围、费用和时效是否确认？",
        "是否保留店铺名称、商品链接或页面截图证据？",
        "图片链接或页面截图是否已经保留，能否追溯到当前候选商品？",
        f"是否需要继续补充字段：{pending_text}？",
    ]


def _score_number(product: dict[str, Any]) -> float:
    score = product.get("score", product.get("total_score", 0))
    if isinstance(score, bool):
        return 0
    if isinstance(score, (int, float)):
        return float(score)
    try:
        return float(score)
    except (TypeError, ValueError):
        return 0


def _matched_indicators(product: dict[str, Any]) -> list[str]:
    detail = product.get("score_detail")
    indicators: list[str] = []
    if isinstance(detail, dict):
        for key in ["category", "title", "dimensions", "material", "color", "style", "service", "price"]:
            item = detail.get(key)
            if not isinstance(item, dict):
                continue
            matched = item.get("matched", [])
            if isinstance(matched, list):
                indicators.extend(str(value) for value in matched if _text(value))
    if not indicators:
        reasons = product.get("reasons")
        if isinstance(reasons, list):
            indicators.extend(_text(reason) for reason in reasons[:3])
    return _unique_text(indicators)


def _risk_tips(product: dict[str, Any], pending_labels: list[str]) -> list[str]:
    risks = product.get("risks")
    tips = [_text(item) for item in risks] if isinstance(risks, list) else []
    if pending_labels:
        tips.append("存在待人工复核字段：" + "、".join(pending_labels))
    return _unique_text(tips or ["采购前需人工确认价格、规格、来源和服务。"])


def _recommendation_level(score: float, pending_count: int, exclusion_reason: str) -> str:
    if exclusion_reason:
        return "建议排除或仅作反例复核"
    if score >= 75 and pending_count <= 2:
        return "优先复核候选"
    if score >= 50:
        return "可复核候选"
    return "低置信度候选"


def _exclusion_reason(product: dict[str, Any]) -> str:
    title = _text(product.get("title"))
    risk_text = _text("；".join(str(item) for item in product.get("risks", []) if _text(item)))
    if any(keyword in title for keyword in UNRELATED_TITLE_KEYWORDS):
        return "标题含有明显无关商品词，建议从候选推荐中排除。"
    if "需排除非办公屏风类商品" in risk_text:
        return "排序规则识别到非办公屏风类风险，建议人工排除。"
    if _score_number(product) < 30 and not any(keyword in title for keyword in SEARCH_KEYWORD_HINTS):
        return "匹配分数较低且标题未命中办公屏风、工位或办公桌等核心词。"
    return ""


def _lower_rank_reason(product: dict[str, Any], rank: int, top_score: float, pending_labels: list[str]) -> str:
    if rank == 1:
        return "排序第1，暂无排名较低原因；仍需完成人工确认。"
    gap = max(0, int(round(top_score - _score_number(product))))
    parts = [f"较第1名低 {gap} 分"] if gap else ["与第1名分数接近"]
    if pending_labels:
        parts.append("待复核字段较多：" + "、".join(pending_labels[:5]))
    else:
        parts.append("主要因关键词、尺寸、材质或服务命中少于前序候选。")
    return "；".join(parts)


def enrich_ranked_products_with_sourcing_guidance(
    ranked_products: list[dict[str, Any]],
    requirements: Any | None = None,
) -> list[dict[str, Any]]:
    top_score = _score_number(ranked_products[0]) if ranked_products else 0
    enriched: list[dict[str, Any]] = []
    for rank, product in enumerate(ranked_products, start=1):
        if not isinstance(product, dict):
            continue
        item = dict(product)
        pending_fields = pending_review_fields(item)
        pending_labels = _field_labels(pending_fields)
        matched = _matched_indicators(item)
        risks = _risk_tips(item, pending_labels)
        exclusion = _exclusion_reason(item)
        level = _recommendation_level(_score_number(item), len(pending_fields), exclusion)
        questions = build_manual_confirmation_questions(item, requirements=requirements)
        why = (
            "第1款在本地规则排序中靠前，主要因为命中采购指标："
            + ("、".join(matched[:6]) if matched else "暂无强命中项")
            + "；采购前仍需人工确认待复核字段。"
            if rank == 1
            else f"第{rank}款作为对比候选保留，需结合分数、待复核字段和页面证据人工判断。"
        )

        item["rank"] = rank
        item["matched_indicators"] = matched
        item["pending_review_fields"] = pending_fields
        item["pending_review_field_labels"] = pending_labels
        item["risk_tips"] = risks
        item["manual_confirmation_questions"] = questions
        item["recommendation_level"] = level
        item["ranking_lower_reason"] = _lower_rank_reason(item, rank, top_score, pending_labels)
        item["exclusion_reason"] = exclusion
        item["recommendation_explanation"] = {
            "why_recommended": why,
            "matched_requirements": matched,
            "pending_review_fields": pending_labels,
            "main_risks": risks,
            "lower_rank_reason": item["ranking_lower_reason"],
            "exclusion_reason": exclusion,
        }
        enriched.append(item)
    return enriched


def _join_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(_text(item) for item in value if _text(item))
    if isinstance(value, dict):
        return "；".join(f"{key}：{_join_csv_value(item)}" for key, item in value.items() if _join_csv_value(item))
    return _text(value)


def build_scoring_table_rows(ranked_products: list[dict[str, Any]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    products = enrich_ranked_products_with_sourcing_guidance(ranked_products) if ranked_products else []
    for rank, product in enumerate(products, start=1):
        rows.append(
            {
                "排名": str(rank),
                "商品名称": _text(product.get("title")) or "待人工复核",
                "平台": _first_text(product.get("platform"), product.get("source")) or "待人工复核",
                "价格": _join_csv_value(product.get("price")) or "待人工复核",
                "尺寸": _text(product.get("dimensions")) or "待人工复核",
                "材质": _text(product.get("material")) or "待人工复核",
                "安装服务": _first_text(product.get("installation_service"), product.get("service_text")) or "待人工复核",
                "商品链接": _text(product.get("url")) or "待人工复核",
                "图片链接": _text(product.get("image_url")) or "待人工复核",
                "匹配分数": _join_csv_value(product.get("score")),
                "命中指标": _join_csv_value(product.get("matched_indicators")),
                "待复核字段": _join_csv_value(product.get("pending_review_field_labels")),
                "风险提示": _join_csv_value(product.get("risk_tips")),
                "人工确认问题": _join_csv_value(product.get("manual_confirmation_questions")),
                "推荐等级": _text(product.get("recommendation_level")),
            }
        )
    return rows


def write_scoring_csv(ranked_products: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = build_scoring_table_rows(ranked_products)
    with path.open("w", encoding="utf-8-sig", newline="") as file_obj:
        writer = csv.DictWriter(file_obj, fieldnames=SCORING_TABLE_HEADERS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def save_sourcing_keywords_json(requirements: Any, output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(generate_sourcing_keywords(requirements), ensure_ascii=False, indent=2), encoding="utf-8")
    return path
