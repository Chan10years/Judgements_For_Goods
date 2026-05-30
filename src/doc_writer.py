from pathlib import Path
from typing import Any

from docx import Document

from src.doc_parser import REQUIRED_HEADERS


def _cell_text(cell) -> str:
    return " ".join(cell.text.split())


def _header_map(table) -> dict[str, int] | None:
    if not table.rows:
        return None

    headers = [_cell_text(cell) for cell in table.rows[0].cells]
    mapping: dict[str, int] = {}

    for required_header in REQUIRED_HEADERS:
        try:
            mapping[required_header] = headers.index(required_header)
        except ValueError:
            return None

    return mapping


def _find_requirements_table(document: Document):
    for table in document.tables:
        mapping = _header_map(table)
        if mapping is not None:
            return table, mapping
    raise ValueError("未找到包含技术参数表头的表格。")


def _format_product_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    return str(value)


def _append_summary_table(document: Document, summary_products: list[dict[str, Any]]) -> None:
    document.add_paragraph()
    document.add_paragraph("候选商品 Top 3（本地规则排序候选商品，非最终采购结论）")

    headers = ["排名", "商品名称", "平台", "价格", "链接", "匹配分数", "匹配理由", "风险提示"]
    table = document.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"

    for index, header in enumerate(headers):
        table.rows[0].cells[index].text = header

    for rank, product in enumerate(summary_products, start=1):
        row = table.add_row().cells
        row[0].text = str(rank)
        row[1].text = _format_product_value(product.get("title"))
        row[2].text = _format_product_value(product.get("platform"))
        row[3].text = _format_product_value(product.get("price"))
        row[4].text = _format_product_value(product.get("url"))
        row[5].text = _format_product_value(product.get("score"))
        row[6].text = _format_product_value(product.get("reasons"))
        row[7].text = _format_product_value(product.get("risks"))


def write_responses(
    input_docx_path: str | Path,
    responses: list[dict[str, str]],
    output_docx_path: str | Path,
    summary_products: list[dict[str, Any]] | None = None,
) -> Path:
    document = Document(str(input_docx_path))
    table, mapping = _find_requirements_table(document)
    response_by_index = {item.get("index", ""): item.get("response_value", "") for item in responses}

    for row_number, row in enumerate(table.rows[1:]):
        cells = row.cells
        index = _cell_text(cells[mapping["序号"]])
        response_value = response_by_index.get(index)
        if response_value is None and row_number < len(responses):
            response_value = responses[row_number].get("response_value", "")
        cells[mapping["投标人响应值"]].text = response_value or ""

    if summary_products:
        _append_summary_table(document, summary_products)

    output_path = Path(output_docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
