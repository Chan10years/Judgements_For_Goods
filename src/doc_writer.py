from pathlib import Path
from typing import Any

from docx import Document

from src.doc_parser import REQUIRED_HEADERS


DELIVERY_OUTPUT_FILE_INDEX = [
    "outputs/recommendation_result.docx",
    "outputs/ranked_products.json",
    "outputs/responses.json",
    "outputs/crawler_products.json",
    "outputs/manual_review_items.json",
    "outputs/manual_review_filled_template.json",
    "outputs/manual_review_validation_report.json",
    "outputs/reviewed_products.json",
    "outputs/review_report.json",
]


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


def _format_metadata_value(value: Any) -> str:
    if value is None:
        return "无"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (list, tuple)):
        return "；".join(_format_metadata_value(item) for item in value) if value else "无"
    if isinstance(value, dict):
        return "；".join(f"{key}：{_format_metadata_value(item)}" for key, item in value.items()) if value else "无"
    text = str(value).strip()
    return text if text else "无"


def _metadata_int(metadata: dict[str, Any], key: str) -> int:
    value = metadata.get(key, 0)
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _append_key_value_table(document: Document, rows: list[tuple[str, Any]]) -> None:
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "项目"
    table.rows[0].cells[1].text = "内容"

    for label, value in rows:
        cells = table.add_row().cells
        cells[0].text = label
        cells[1].text = _format_metadata_value(value)


def _add_paragraph(document: Document, text: str, style: str | None = None) -> None:
    if style is None:
        document.add_paragraph(text)
        return
    try:
        document.add_paragraph(text, style=style)
    except KeyError:
        document.add_paragraph(text)


def _append_delivery_summary(document: Document) -> None:
    document.add_heading("交付报告摘要", level=1)
    document.add_paragraph(
        "本报告为采购辅助候选报告，基于当前可用商品数据和本地规则生成候选与响应建议；"
        "所有候选、字段和证据均需要人工复核，不代表最终采购结论。"
    )


def _append_data_source_section(document: Document, metadata: dict[str, Any]) -> None:
    priority = metadata.get(
        "data_source_priority",
        ["reviewed_products.json", "crawler_products.json", "sample_products.json"],
    )

    document.add_heading("数据来源说明", level=1)
    document.add_paragraph("本次商品数据来源优先级如下：")
    for source in priority:
        _add_paragraph(document, _format_metadata_value(source), style="List Number")

    _append_key_value_table(
        document,
        [
            ("当前实际使用数据源", metadata.get("actual_data_source", "未识别")),
            ("当前数据源路径", metadata.get("products_source_path", "未提供")),
            ("说明", metadata.get("data_source_note", "按可用数据源优先级自动选择。")),
        ],
    )


def _append_recommendation_summary_section(document: Document, metadata: dict[str, Any]) -> None:
    output_paths = metadata.get("output_paths", {})
    document.add_heading("推荐结果摘要", level=1)
    _append_key_value_table(
        document,
        [
            ("需求数量", _metadata_int(metadata, "requirements_count")),
            ("候选商品数量", _metadata_int(metadata, "products_count")),
            ("排序后候选商品数量", _metadata_int(metadata, "ranked_products_count")),
            ("Top候选数量", _metadata_int(metadata, "top_products_count")),
            ("Word输出文件路径", output_paths.get("recommendation_result_docx")),
            ("排序结果文件路径", output_paths.get("ranked_products_json")),
            ("响应结果文件路径", output_paths.get("responses_json")),
        ],
    )


def _append_review_status_section(document: Document, metadata: dict[str, Any]) -> None:
    review_status = metadata.get("review_status", {})
    if not isinstance(review_status, dict):
        review_status = {}

    document.add_heading("人工复核状态说明", level=1)
    _append_key_value_table(
        document,
        [
            ("存在 reviewed_products.json", review_status.get("has_reviewed_products", False)),
            ("存在 review_report.json", review_status.get("has_review_report", False)),
            ("已复核商品数量", review_status.get("reviewed_products_count", 0)),
            ("approved 数量", review_status.get("approved_count", 0)),
            ("rejected 数量", review_status.get("rejected_count", 0)),
            ("needs_more_info 数量", review_status.get("needs_more_info_count", 0)),
            ("未匹配复核项数量", review_status.get("unmatched_review_items_count", 0)),
            ("仍需人工复核提示", review_status.get("risk_note", "仍需人工确认候选商品与关键字段。")),
        ],
    )


def _append_field_risk_section(document: Document) -> None:
    document.add_heading("字段风险提示", level=1)
    document.add_paragraph(
        "价格、尺寸、材质、安装服务、来源、证据文本等字段如缺失、为空或证据不足，"
        "需要人工确认；未确认字段不得写成已确认，也不得直接作为采购决策依据。"
    )
    for item in [
        "价格：如缺少币种、含税口径、运费或时效信息，需要人工确认。",
        "尺寸：如未覆盖长宽高、厚度、屏风高度或适配场景，需要人工确认。",
        "材质：如只有营销描述、没有明确材料或结构信息，需要人工确认。",
        "安装服务：如未说明是否含安装、配送、售后或现场条件，需要人工确认。",
        "来源与证据文本：如缺少链接、来源、截图摘录或证据文本，需要人工确认。",
    ]:
        _add_paragraph(document, item, style="List Bullet")


def _append_output_index_section(document: Document, metadata: dict[str, Any]) -> None:
    files = metadata.get("output_file_index") or DELIVERY_OUTPUT_FILE_INDEX
    document.add_heading("输出文件索引", level=1)
    for file_path in files:
        _add_paragraph(document, _format_metadata_value(file_path), style="List Bullet")


def _append_delivery_report(document: Document, delivery_metadata: dict[str, Any]) -> None:
    document.add_page_break()
    _append_delivery_summary(document)
    _append_data_source_section(document, delivery_metadata)
    _append_recommendation_summary_section(document, delivery_metadata)
    _append_review_status_section(document, delivery_metadata)
    _append_field_risk_section(document)
    _append_output_index_section(document, delivery_metadata)


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
    delivery_metadata: dict[str, Any] | None = None,
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

    if delivery_metadata:
        _append_delivery_report(document, delivery_metadata)

    output_path = Path(output_docx_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(output_path))
    return output_path
