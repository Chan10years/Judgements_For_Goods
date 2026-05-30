import hashlib
import json
import re
from pathlib import Path
from typing import Any


LEGACY_PRODUCT_FIELDS = [
    "platform",
    "title",
    "price",
    "shop",
    "url",
    "image_url",
    "specs_text",
    "service_text",
    "raw_text",
]

STANDARD_PRODUCT_FIELDS = [
    "product_id",
    "title",
    "brand",
    "category",
    "price",
    "material",
    "color",
    "dimensions",
    "style",
    "source",
    "url",
    "notes",
    "specs_text",
    "service_text",
    "raw_text",
]

PRODUCT_FIELDS = list(dict.fromkeys(LEGACY_PRODUCT_FIELDS + STANDARD_PRODUCT_FIELDS))
TEXT_FIELDS = [field for field in PRODUCT_FIELDS if field != "price"]
BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTS_PATH = BASE_DIR / "data" / "products.json"
DEFAULT_SAMPLE_PRODUCTS_PATH = BASE_DIR / "data" / "sample_products.json"


def _text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _first_text(item: dict[str, Any], *fields: str) -> str:
    for field in fields:
        value = _text(item.get(field))
        if value:
            return value
    return ""


def _normalize_price(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value) if float(value).is_integer() else float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("￥", "").replace("¥", "")
        match = re.search(r"\d+(?:\.\d+)?", cleaned)
        if not match:
            return None
        number = float(match.group(0))
        return int(number) if number.is_integer() else number
    return None


def _infer_product_id(item: dict[str, Any], title: str, url: str, raw_text: str) -> str:
    explicit_id = _first_text(item, "product_id", "id", "sku")
    if explicit_id:
        return explicit_id
    basis = "|".join([title, url, raw_text])
    digest = hashlib.sha1(basis.encode("utf-8")).hexdigest()[:12]
    return f"local-{digest}"


def _infer_dimensions(*texts: str) -> str:
    joined = " ".join(text for text in texts if text)
    match = re.search(r"\d+(?:\.\d+)?\s*[xX×*]\s*\d+(?:\.\d+)?\s*[xX×*]\s*\d+(?:\.\d+)?\s*(?:mm|毫米)?", joined)
    return _text(match.group(0)) if match else ""


def _infer_category(title: str, raw_text: str) -> str:
    text = f"{title} {raw_text}"
    if any(keyword in text for keyword in ["办公屏风", "屏风", "工位", "办公桌", "卡位", "隔断"]):
        return "办公家具"
    if any(keyword in text for keyword in ["水壶", "烧水", "家用"]):
        return "生活用品"
    return ""


def normalize_product(product: dict[str, Any]) -> dict[str, Any]:
    """Return a stable product shape while tolerating missing optional fields."""
    if not isinstance(product, dict):
        raise ValueError("商品数据项必须是对象。")

    title = _first_text(product, "title", "name")
    specs_text = _first_text(product, "specs_text", "specs", "description")
    service_text = _first_text(product, "service_text", "service")
    raw_text = _first_text(product, "raw_text", "raw", "description")
    if not raw_text:
        raw_text = _text("；".join(part for part in [title, specs_text, service_text] if part))

    source = _first_text(product, "source", "platform") or "本地测试数据"
    platform = _first_text(product, "platform", "source") or source
    url = _first_text(product, "url", "link")
    shop = _first_text(product, "shop", "seller", "store")
    brand = _first_text(product, "brand")
    category = _first_text(product, "category") or _infer_category(title, raw_text)
    dimensions = _first_text(product, "dimensions", "size") or _infer_dimensions(title, specs_text, raw_text)

    normalized: dict[str, Any] = {
        "platform": platform,
        "title": title,
        "price": _normalize_price(product.get("price")),
        "shop": shop,
        "url": url,
        "image_url": _first_text(product, "image_url", "image"),
        "specs_text": specs_text,
        "service_text": service_text,
        "raw_text": raw_text,
        "product_id": "",
        "brand": brand,
        "category": category,
        "material": _first_text(product, "material"),
        "color": _first_text(product, "color"),
        "dimensions": dimensions,
        "style": _first_text(product, "style"),
        "source": source,
        "notes": _first_text(product, "notes", "note"),
    }
    normalized["product_id"] = _infer_product_id(product, title, url, raw_text)

    return {field: normalized.get(field, "") for field in PRODUCT_FIELDS}


def normalize_products(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(products, list):
        raise ValueError("商品数据必须是数组。")
    return [normalize_product(item) for item in products if isinstance(item, dict)]


def validate_product(product: dict[str, Any]) -> bool:
    if not isinstance(product, dict):
        return False

    normalized = normalize_product(product)
    price = normalized.get("price")
    price_valid = price is None or (isinstance(price, (int, float)) and not isinstance(price, bool))
    has_text = any(_text(normalized.get(field)) for field in ["title", "specs_text", "raw_text"])
    return price_valid and has_text


def load_products_json(path: str | Path) -> list[dict[str, Any]]:
    product_path = Path(path)
    if not product_path.exists():
        raise FileNotFoundError(f"商品 JSON 不存在：{product_path}")

    try:
        data = json.loads(product_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"商品 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

    if isinstance(data, dict) and isinstance(data.get("products"), list):
        data = data["products"]
    if not isinstance(data, list):
        raise ValueError("商品 JSON 顶层必须是数组，或包含 products 数组。")

    return normalize_products(data)


def load_products(path: str | Path) -> list[dict[str, Any]]:
    return load_products_json(path)


def _field_check(products: list[dict[str, Any]]) -> str:
    missing_messages: list[str] = []
    invalid_indexes: list[str] = []
    for index, product in enumerate(products, start=1):
        missing = [field for field in PRODUCT_FIELDS if field not in product]
        if missing:
            missing_messages.append(f"第 {index} 条缺少字段：{', '.join(missing)}")
        if not validate_product(product):
            invalid_indexes.append(str(index))

    messages: list[str] = []
    if missing_messages:
        messages.append("字段检查未通过：" + "；".join(missing_messages))
    else:
        messages.append("字段检查通过。")
    if invalid_indexes:
        messages.append("校验提示：以下商品缺少可用于匹配的基础文本：" + ", ".join(invalid_indexes))
    return " ".join(messages)


def _print_load_result(path: Path, label: str) -> None:
    products = load_products_json(path)
    print(f"{label}：{path}")
    print(f"商品数量：{len(products)}")
    print(_field_check(products))


def main() -> int:
    try:
        _print_load_result(DEFAULT_PRODUCTS_PATH, "阶段 2-4 本地商品")
        if DEFAULT_SAMPLE_PRODUCTS_PATH.exists():
            _print_load_result(DEFAULT_SAMPLE_PRODUCTS_PATH, "阶段 5-7 本地测试商品")
    except Exception as exc:
        print(f"商品数据检查失败：{exc}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
