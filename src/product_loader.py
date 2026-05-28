import json
from pathlib import Path
from typing import Any


PRODUCT_FIELDS = [
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

TEXT_FIELDS = [field for field in PRODUCT_FIELDS if field != "price"]
DEFAULT_PRODUCTS_PATH = Path(__file__).resolve().parents[1] / "data" / "products.json"


def normalize_product(item: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(item, dict):
        raise ValueError("商品数据项必须是对象。")

    normalized: dict[str, Any] = {}
    for field in TEXT_FIELDS:
        value = item.get(field, "")
        normalized[field] = "" if value is None else str(value)

    price = item.get("price", None)
    if isinstance(price, bool) or (price is not None and not isinstance(price, (int, float))):
        raise ValueError("price 字段必须是数字或 null。")
    normalized["price"] = price

    return {field: normalized[field] for field in PRODUCT_FIELDS}


def load_products(path: str | Path) -> list[dict[str, Any]]:
    product_path = Path(path)
    if not product_path.exists():
        raise FileNotFoundError(f"商品 JSON 不存在：{product_path}")

    try:
        data = json.loads(product_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"商品 JSON 格式错误：第 {exc.lineno} 行第 {exc.colno} 列，{exc.msg}") from exc

    if not isinstance(data, list):
        raise ValueError("商品 JSON 顶层必须是数组。")

    products: list[dict[str, Any]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 条商品数据错误：商品数据项必须是对象。")
        missing_fields = [field for field in PRODUCT_FIELDS if field not in item]
        if missing_fields:
            raise ValueError(f"第 {index} 条商品缺少字段：{', '.join(missing_fields)}")
        try:
            products.append(normalize_product(item))
        except ValueError as exc:
            raise ValueError(f"第 {index} 条商品数据错误：{exc}") from exc

    return products


def _field_check(products: list[dict[str, Any]]) -> str:
    missing_messages: list[str] = []
    for index, product in enumerate(products, start=1):
        missing = [field for field in PRODUCT_FIELDS if field not in product]
        if missing:
            missing_messages.append(f"第 {index} 条缺少字段：{', '.join(missing)}")

    if missing_messages:
        return "字段检查未通过；" + "；".join(missing_messages)
    return "字段检查通过。"


def main() -> int:
    try:
        products = load_products(DEFAULT_PRODUCTS_PATH)
    except Exception as exc:
        print(f"商品数据检查失败：{exc}")
        return 1

    print(f"商品数量：{len(products)}")
    print(_field_check(products))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
