import json
from pathlib import Path

from docx import Document


REQUIRED_HEADERS = ["序号", "技术参数名称", "单位", "项目需求值或表述", "投标人响应值"]


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


def parse_requirements(docx_path: str | Path) -> list[dict[str, str]]:
    document = Document(str(docx_path))
    table, mapping = _find_requirements_table(document)
    requirements: list[dict[str, str]] = []

    for row in table.rows[1:]:
        cells = row.cells
        index = _cell_text(cells[mapping["序号"]])
        name = _cell_text(cells[mapping["技术参数名称"]])
        unit = _cell_text(cells[mapping["单位"]])
        required_value = _cell_text(cells[mapping["项目需求值或表述"]])
        response_value = _cell_text(cells[mapping["投标人响应值"]])

        if not any([index, name, unit, required_value, response_value]):
            continue

        requirements.append(
            {
                "index": index,
                "name": name,
                "unit": unit,
                "required_value": required_value,
                "response_value": response_value,
            }
        )

    return requirements


def save_requirements_json(requirements: list[dict[str, str]], output_path: str | Path) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(requirements, ensure_ascii=False, indent=2), encoding="utf-8")
