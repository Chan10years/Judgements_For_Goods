from pathlib import Path

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


def write_responses(
    input_docx_path: str | Path,
    responses: list[dict[str, str]],
    output_docx_path: str | Path,
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

    output_path = Path(output_docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
