from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

try:
    from bs4 import BeautifulSoup
except ModuleNotFoundError:
    BeautifulSoup = None  # type: ignore[assignment]

from src.crawler.models import SeedUrl


PRICE_PATTERNS = [
    re.compile(r"(?:￥|¥|RMB\s*)\s*(\d+(?:,\d{3})*(?:\.\d+)?)", re.IGNORECASE),
    re.compile(r"价格[:：\s]*(\d+(?:,\d{3})*(?:\.\d+)?)"),
]
SPEC_KEYWORDS = ["规格", "参数", "尺寸", "材质", "颜色", "型号", "款式", "承重", "环保", "五金"]
SERVICE_KEYWORDS = ["配送", "送货", "安装", "售后", "质保", "保修", "shipping", "delivery", "warranty"]
REQUIRED_OUTPUT_FIELDS = ["title", "price", "specs_text", "service_text"]


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split())


def _first_non_empty(*values: Any) -> str:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _meta_content(soup: BeautifulSoup, *names: str) -> str:
    for name in names:
        tag = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if tag and tag.get("content"):
            return _clean_text(tag.get("content"))
    return ""


def _visible_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    return _clean_text(soup.get_text(" "))


def _json_ld_values(soup: BeautifulSoup) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        text = script.string or script.get_text()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            values.append(data)
            graph = data.get("@graph")
            if isinstance(graph, list):
                values.extend(item for item in graph if isinstance(item, dict))
        elif isinstance(data, list):
            values.extend(item for item in data if isinstance(item, dict))
    return values


def _extract_json_ld_product(soup: BeautifulSoup) -> dict[str, Any]:
    for item in _json_ld_values(soup):
        item_type = item.get("@type")
        type_text = " ".join(item_type) if isinstance(item_type, list) else str(item_type or "")
        if "Product" not in type_text:
            continue
        offers = item.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name", "")
        image = item.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        return {
            "title": _clean_text(item.get("name")),
            "brand": _clean_text(brand),
            "price": _clean_text(offers.get("price")) if isinstance(offers, dict) else "",
            "image_url": _clean_text(image),
            "description": _clean_text(item.get("description")),
        }
    return {}


class _FallbackHTMLSnapshot(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.meta: dict[str, str] = {}
        self.text_parts: list[str] = []
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.script_type = ""
        self.script_buffer: list[str] = []
        self.json_ld_scripts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        self.stack.append(tag)
        attr_map = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = attr_map.get("name") or attr_map.get("property")
            content = attr_map.get("content")
            if key and content:
                self.meta[key] = _clean_text(content)
        if tag == "script":
            self.script_type = attr_map.get("type", "").lower()
            self.script_buffer = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "script" and self.script_type == "application/ld+json":
            script_text = "".join(self.script_buffer).strip()
            if script_text:
                self.json_ld_scripts.append(script_text)
        if tag in self.stack:
            reverse_index = len(self.stack) - 1 - self.stack[::-1].index(tag)
            del self.stack[reverse_index:]
        self.script_type = ""
        self.script_buffer = []

    def handle_data(self, data: str) -> None:
        cleaned = _clean_text(data)
        if not cleaned:
            return
        if self.stack and self.stack[-1] == "script":
            self.script_buffer.append(data)
            return
        if any(tag in self.stack for tag in ["style", "noscript", "svg"]):
            return
        self.text_parts.append(cleaned)
        if "title" in self.stack:
            self.title_parts.append(cleaned)
        if "h1" in self.stack:
            self.h1_parts.append(cleaned)


def _json_ld_product_from_scripts(scripts: list[str]) -> dict[str, Any]:
    values: list[dict[str, Any]] = []
    for script in scripts:
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            values.append(data)
            graph = data.get("@graph")
            if isinstance(graph, list):
                values.extend(item for item in graph if isinstance(item, dict))
        elif isinstance(data, list):
            values.extend(item for item in data if isinstance(item, dict))

    for item in values:
        item_type = item.get("@type")
        type_text = " ".join(item_type) if isinstance(item_type, list) else str(item_type or "")
        if "Product" not in type_text:
            continue
        offers = item.get("offers")
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        brand = item.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name", "")
        image = item.get("image", "")
        if isinstance(image, list):
            image = image[0] if image else ""
        return {
            "title": _clean_text(item.get("name")),
            "brand": _clean_text(brand),
            "price": _clean_text(offers.get("price")) if isinstance(offers, dict) else "",
            "image_url": _clean_text(image),
            "description": _clean_text(item.get("description")),
        }
    return {}


def _seed_context(seed: SeedUrl | dict[str, Any], final_url: str = "") -> dict[str, str]:
    seed_url = seed.url if isinstance(seed, SeedUrl) else str(seed.get("url", ""))
    return {
        "source_name": seed.source_name if isinstance(seed, SeedUrl) else str(seed.get("source_name", "")),
        "category_hint": seed.category_hint if isinstance(seed, SeedUrl) else str(seed.get("category_hint", "")),
        "note": seed.note if isinstance(seed, SeedUrl) else str(seed.get("note", "")),
        "seed_url": seed_url,
        "url": final_url or seed_url,
    }


def _build_parsed_product(
    context: dict[str, str],
    title: str,
    brand: str,
    description: str,
    h1_text: str,
    price: str,
    image_url: str,
    specs_text: str,
    service_text: str,
    raw_text: str,
) -> dict[str, Any]:
    evidence_parts = [description, h1_text, specs_text, service_text]
    evidence_text = "；".join(part for part in evidence_parts if part)[:2000]
    parsed = {
        "platform": context["source_name"],
        "title": title,
        "brand": brand,
        "category": context["category_hint"],
        "price": price,
        "shop": "",
        "url": context["url"],
        "image_url": image_url,
        "material": "",
        "color": "",
        "dimensions": "",
        "style": "",
        "source": context["source_name"],
        "notes": context["note"],
        "specs_text": specs_text,
        "service_text": service_text,
        "raw_text": raw_text[:2000],
        "meta_description": description,
        "h1": h1_text,
        "evidence": evidence_text,
        "evidence_text": evidence_text,
    }
    missing_fields = [field for field in REQUIRED_OUTPUT_FIELDS if not _clean_text(parsed.get(field))]
    parsed["missing_fields"] = missing_fields
    parsed["manual_review_required"] = bool(missing_fields)
    parsed["parse_success"] = bool(_clean_text(parsed["title"]))
    parsed["parse_error"] = "" if parsed["parse_success"] else "页面缺少标题，无法确认商品信息。"
    return parsed


def _parse_product_page_stdlib(html: str, seed: SeedUrl | dict[str, Any], final_url: str = "") -> dict[str, Any]:
    context = _seed_context(seed, final_url=final_url)
    snapshot = _FallbackHTMLSnapshot()
    snapshot.feed(html or "")
    json_ld_product = _json_ld_product_from_scripts(snapshot.json_ld_scripts)
    raw_text = _clean_text(" ".join(snapshot.text_parts))[:2000]
    lines = [line.strip() for line in re.split(r"[\r\n。；;]+", raw_text) if line.strip()]
    description = _first_non_empty(
        snapshot.meta.get("description"),
        snapshot.meta.get("og:description"),
        json_ld_product.get("description", ""),
    )
    h1_text = "；".join(snapshot.h1_parts[:5])
    specs_text = _lines_with_keywords(lines, SPEC_KEYWORDS)
    service_text = _lines_with_keywords(lines, SERVICE_KEYWORDS)
    title = _first_non_empty(
        json_ld_product.get("title"),
        snapshot.meta.get("og:title"),
        h1_text,
        " ".join(snapshot.title_parts),
    )
    return _build_parsed_product(
        context=context,
        title=title,
        brand=_clean_text(json_ld_product.get("brand")),
        description=description,
        h1_text=h1_text,
        price=_extract_price(raw_text, json_ld_product),
        image_url=_clean_text(json_ld_product.get("image_url")),
        specs_text=specs_text,
        service_text=service_text,
        raw_text=raw_text,
    )


def _extract_price(text: str, json_ld_product: dict[str, Any]) -> str:
    if json_ld_product.get("price"):
        return _clean_text(json_ld_product.get("price"))
    for pattern in PRICE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).replace(",", "")
    return ""


def _lines_with_keywords(lines: list[str], keywords: list[str], limit: int = 12) -> str:
    matched: list[str] = []
    for line in lines:
        if any(keyword.lower() in line.lower() for keyword in keywords):
            matched.append(line)
        if len(matched) >= limit:
            break
    return "；".join(matched)


def _table_text(soup: BeautifulSoup) -> str:
    rows: list[str] = []
    for row in soup.find_all("tr"):
        cells = [_clean_text(cell.get_text(" ")) for cell in row.find_all(["th", "td"])]
        cells = [cell for cell in cells if cell]
        if cells:
            rows.append("：".join(cells))
    return "；".join(rows[:20])


def parse_product_page(html: str, seed: SeedUrl | dict[str, Any], final_url: str = "") -> dict[str, Any]:
    if BeautifulSoup is None:
        return _parse_product_page_stdlib(html, seed, final_url=final_url)

    context = _seed_context(seed, final_url=final_url)

    soup = BeautifulSoup(html or "", "html.parser")
    json_ld_product = _extract_json_ld_product(soup)
    title_tag = soup.find("title")
    h1_tags = [_clean_text(tag.get_text(" ")) for tag in soup.find_all("h1")]
    description = _first_non_empty(
        _meta_content(soup, "description", "og:description"),
        json_ld_product.get("description", ""),
    )
    raw_text = _visible_text(soup)[:2000]
    lines = [line.strip() for line in re.split(r"[\r\n。；;]+", raw_text) if line.strip()]
    specs_text = _first_non_empty(_table_text(soup), _lines_with_keywords(lines, SPEC_KEYWORDS))
    service_text = _lines_with_keywords(lines, SERVICE_KEYWORDS)
    return _build_parsed_product(
        context=context,
        title=_first_non_empty(
            json_ld_product.get("title"),
            _meta_content(soup, "og:title"),
            *(h1_tags[:1]),
            title_tag.get_text(" ") if title_tag else "",
        ),
        brand=_clean_text(json_ld_product.get("brand")),
        description=description,
        h1_text="；".join(h1_tags[:5]),
        price=_extract_price(raw_text, json_ld_product),
        image_url=_clean_text(json_ld_product.get("image_url")),
        specs_text=specs_text,
        service_text=service_text,
        raw_text=raw_text,
    )
