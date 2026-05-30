from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any, Callable

from main import (
    build_marketplace_search_links,
    run_pipeline,
    run_stage14_v2a_delivery,
    run_stage15_smart_sourcing_delivery,
)
from src.crawler.pipeline import run_crawler
from src.crawler.review_apply import apply_manual_reviews, write_empty_review_outputs
from src.crawler.review_template import generate_review_template
from src.crawler.review_validate import validate_review_filled, write_empty_validation_report


BASE_DIR = Path(__file__).resolve().parent

PATHS = {
    "word_input": BASE_DIR / "data" / "办公屏风01模板样例.docx",
    "sample_products": BASE_DIR / "data" / "sample_products.json",
    "seed_urls": BASE_DIR / "data" / "seed_urls.json",
    "crawler_products": BASE_DIR / "outputs" / "crawler_products.json",
    "manual_review_items": BASE_DIR / "outputs" / "manual_review_items.json",
    "manual_review_filled_template": BASE_DIR / "outputs" / "manual_review_filled_template.json",
    "manual_review_validation_report": BASE_DIR / "outputs" / "manual_review_validation_report.json",
    "reviewed_products": BASE_DIR / "outputs" / "reviewed_products.json",
    "review_report": BASE_DIR / "outputs" / "review_report.json",
    "recommendation_result": BASE_DIR / "outputs" / "recommendation_result.docx",
    "data_review_filled": BASE_DIR / "data" / "manual_review_filled.json",
    "outputs_review_filled": BASE_DIR / "outputs" / "manual_review_filled.json",
}

MAIN_INPUT_PATH_KEYS = [
    "word_input",
    "sample_products",
    "seed_urls",
    "crawler_products",
    "manual_review_items",
    "manual_review_filled_template",
    "manual_review_validation_report",
    "reviewed_products",
    "review_report",
    "recommendation_result",
]

FILE_STATUS_KEYS = [
    ("Word输入", "word_input"),
    ("crawler_products", "crawler_products"),
    ("manual_review_items", "manual_review_items"),
    ("manual_review_filled_template", "manual_review_filled_template"),
    ("manual_review_validation_report", "manual_review_validation_report"),
    ("reviewed_products", "reviewed_products"),
    ("review_report", "review_report"),
    ("recommendation_result.docx", "recommendation_result"),
]

SESSION_RESULT_KEY = "stage12_last_operation_result"
STAGE13_2B_SESSION_RESULT_KEY = "stage13_2b_last_operation_result"
STAGE15_SESSION_RESULT_KEY = "stage15_last_operation_result"
STAGE13_2B_UPLOAD_DIR = BASE_DIR / "outputs" / "stage13_2b_uploads"


@dataclass
class OperationResult:
    name: str
    success: bool
    summary: str
    output_paths: list[str]
    error: str = ""
    details: dict[str, Any] | None = None


def _load_streamlit() -> Any:
    import streamlit as st

    return st


def _relative_path(path: str | Path) -> str:
    resolved = Path(path)
    try:
        return str(resolved.relative_to(BASE_DIR))
    except ValueError:
        return str(resolved)


def _path_list(*items: Any) -> list[str]:
    paths: list[str] = []
    for item in items:
        if isinstance(item, dict):
            paths.extend(_path_list(*item.values()))
            continue
        if not item:
            continue
        paths.append(_relative_path(item))
    return list(dict.fromkeys(paths))


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return _relative_path(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _safe_upload_filename(filename: str, fallback: str) -> str:
    name = Path(filename or fallback).name
    name = re.sub(r"[^0-9A-Za-z._\-\u4e00-\u9fff]+", "_", name).strip("._")
    return name or fallback


def _save_uploaded_file(uploaded_file: Any, upload_dir: Path = STAGE13_2B_UPLOAD_DIR) -> Path:
    upload_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    filename = _safe_upload_filename(getattr(uploaded_file, "name", ""), "uploaded_file")
    output_path = upload_dir / f"{timestamp}_{filename}"
    output_path.write_bytes(uploaded_file.getbuffer())
    return output_path


def _select_review_filled_path() -> Path | None:
    for path in [PATHS["data_review_filled"], PATHS["outputs_review_filled"]]:
        if path.exists() and path.stat().st_size > 0:
            return path
    return None


def _safe_count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        for key in ["review_items", "products", "items"]:
            if isinstance(value.get(key), list):
                return len(value[key])
    return 0


def run_crawler_action() -> OperationResult:
    report = run_crawler()
    output_paths = report.get("output_paths", {})
    summary = (
        f"URL总数 {report.get('total_url_count', 0)}，"
        f"有效URL {report.get('valid_url_count', 0)}，"
        f"成功 {report.get('success_count', 0)}，"
        f"失败 {report.get('failure_count', 0)}，"
        f"跳过 {report.get('skipped_count', 0)}，"
        f"需人工复核 {len(report.get('manual_review_items', []))} 项。"
    )
    return OperationResult(
        name="运行公开URL采集",
        success=True,
        summary=summary,
        output_paths=_path_list(output_paths),
        details=_json_safe(report.get("summary", report)),
    )


def run_main_pipeline_action() -> OperationResult:
    result = run_pipeline()
    summary = (
        f"需求项 {result.get('requirements_count', 0)} 条，"
        f"候选商品 {result.get('products_count', 0)} 个，"
        f"排序商品 {result.get('ranked_products_count', 0)} 个，"
        f"Top候选 {result.get('top_products_count', 0)} 个，"
        f"响应项 {result.get('responses_count', 0)} 条。"
    )
    paths = [value for key, value in result.items() if key.endswith("_path")]
    return OperationResult(
        name="运行主推荐流程",
        success=True,
        summary=summary,
        output_paths=_path_list(*paths),
        details=_json_safe(result),
    )


def run_stage14_v2a_delivery_action(word_path: str | Path, candidate_path: str | Path) -> OperationResult:
    output_dir = BASE_DIR / "outputs" / "stage14_v2a_mvp" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result = run_stage14_v2a_delivery(word_path, candidate_path, output_dir=output_dir)
    summary = (
        f"需求项 {result.get('requirements_count', 0)} 条，"
        f"候选商品 {result.get('products_count', 0)} 个，"
        f"Top候选 {result.get('top_products_count', 0)} 个。"
    )
    paths = [
        result.get("requirements_path"),
        result.get("ranked_products_path"),
        result.get("responses_path"),
        result.get("output_docx_path"),
        result.get("imported_candidate_products_path"),
    ]
    return OperationResult(
        name="V2-A 浏览器辅助式寻源 MVP",
        success=True,
        summary=summary,
        output_paths=_path_list(*paths),
        details=_json_safe(result),
    )


def run_stage15_smart_sourcing_action(word_path: str | Path, candidate_path: str | Path) -> OperationResult:
    output_dir = BASE_DIR / "outputs" / "stage15_v2a_plus" / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    result = run_stage15_smart_sourcing_delivery(word_path, candidate_path, output_dir=output_dir)
    summary = (
        f"需求项 {result.get('requirements_count', 0)} 条，"
        f"候选商品 {result.get('products_count', 0)} 个，"
        f"Top候选 {result.get('top_products_count', 0)} 个，"
        f"评分表 { _relative_path(result.get('scoring_csv_path', '')) if result.get('scoring_csv_path') else '未生成' }。"
    )
    paths = [
        result.get("requirements_path"),
        result.get("ranked_products_path"),
        result.get("responses_path"),
        result.get("output_docx_path"),
        result.get("imported_candidate_products_path"),
        result.get("scoring_csv_path"),
    ]
    return OperationResult(
        name="V2-A+ 智能寻源助手",
        success=True,
        summary=summary,
        output_paths=_path_list(*paths),
        details=_json_safe(result),
    )


def run_stage13_2b_delivery_action(word_path: str | Path, candidate_path: str | Path) -> OperationResult:
    return run_stage14_v2a_delivery_action(word_path, candidate_path)


def generate_review_template_action() -> OperationResult:
    template = generate_review_template()
    count = _safe_count(template)
    return OperationResult(
        name="生成复核填写模板",
        success=True,
        summary=f"已生成客户复核填写模板，复核项 {count} 条。",
        output_paths=_path_list(PATHS["manual_review_filled_template"]),
        details={"review_items_count": count},
    )


def validate_review_filled_action() -> OperationResult:
    review_path = _select_review_filled_path()
    if review_path is None:
        report = write_empty_validation_report(
            review_filled_path=None,
            products_path=PATHS["crawler_products"],
            output_report_path=PATHS["manual_review_validation_report"],
        )
        return OperationResult(
            name="校验复核填写文件",
            success=True,
            summary="未发现客户填写后的复核文件，已生成空校验报告。",
            output_paths=_path_list(PATHS["manual_review_validation_report"]),
            details=_json_safe(report),
        )

    report = validate_review_filled(
        review_path,
        products_path=PATHS["crawler_products"],
        output_report_path=PATHS["manual_review_validation_report"],
    )
    summary = (
        f"使用 {_relative_path(review_path)}，"
        f"复核项 {report.get('total_items', 0)} 条，"
        f"错误 {report.get('error_count', 0)} 个，"
        f"警告 {report.get('warning_count', 0)} 个。"
    )
    return OperationResult(
        name="校验复核填写文件",
        success=True,
        summary=summary,
        output_paths=_path_list(PATHS["manual_review_validation_report"]),
        details=_json_safe(report),
    )


def apply_review_action() -> OperationResult:
    review_path = _select_review_filled_path()
    if review_path is None:
        validation_report = write_empty_validation_report(
            review_filled_path=None,
            products_path=PATHS["crawler_products"],
            output_report_path=PATHS["manual_review_validation_report"],
        )
        review_report = write_empty_review_outputs(
            products_path=PATHS["crawler_products"],
            review_filled_path=None,
            output_products_path=PATHS["reviewed_products"],
            output_report_path=PATHS["review_report"],
        )
        details = {"validation_report": validation_report, "review_report": review_report}
        return OperationResult(
            name="执行复核回填",
            success=True,
            summary="未发现客户填写后的复核文件，本次没有可回填项。",
            output_paths=_path_list(
                PATHS["manual_review_validation_report"],
                PATHS["reviewed_products"],
                PATHS["review_report"],
            ),
            details=_json_safe(details),
        )

    report = apply_manual_reviews(
        products_path=PATHS["crawler_products"],
        review_filled_path=review_path,
        output_products_path=PATHS["reviewed_products"],
        output_report_path=PATHS["review_report"],
    )
    summary = (
        f"使用 {_relative_path(review_path)}，"
        f"已复核商品 {report.get('reviewed_products_count', 0)} 个，"
        f"approved {report.get('approved_count', 0)} 个，"
        f"rejected {report.get('rejected_count', 0)} 个，"
        f"needs_more_info {report.get('needs_more_info_count', 0)} 个。"
    )
    return OperationResult(
        name="执行复核回填",
        success=True,
        summary=summary,
        output_paths=_path_list(
            PATHS["manual_review_validation_report"],
            PATHS["reviewed_products"],
            PATHS["review_report"],
        ),
        details=_json_safe(report),
    )


def _capture_action(name: str, action: Callable[[], OperationResult]) -> OperationResult:
    try:
        return action()
    except Exception as exc:
        return OperationResult(name=name, success=False, summary="操作未完成。", output_paths=[], error=str(exc))


def _main_input_rows() -> list[dict[str, str]]:
    return [{"路径": _relative_path(PATHS[key])} for key in MAIN_INPUT_PATH_KEYS]


def _file_status_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for label, key in FILE_STATUS_KEYS:
        path = PATHS[key]
        rows.append(
            {
                "文件": label,
                "路径": _relative_path(path),
                "状态": "存在" if path.exists() else "未发现",
            }
        )
    return rows


def _render_result(st: Any, result: OperationResult) -> None:
    st.subheader("运行结果摘要")
    if result.success:
        st.success("成功")
    else:
        st.error("失败")

    st.write(result.summary)

    st.markdown("**输出文件路径**")
    if result.output_paths:
        for path in result.output_paths:
            st.code(path)
    else:
        st.write("无新增输出文件。")

    st.markdown("**错误信息**")
    st.write(result.error or "无")

    if result.details:
        with st.expander("查看结构化摘要"):
            st.json(result.details)


def _render_marketplace_search(st: Any, search: dict[str, Any] | None = None) -> None:
    search = search or build_marketplace_search_links()
    st.markdown("**智能搜索词与淘宝/京东寻源辅助**")
    st.info(
        search.get(
            "notice",
            "当前 V2-A+ 提供智能寻源辅助入口。客户在自己的浏览器中正常登录并人工确认候选商品后，"
            "通过候选商品文件或候选链接/文本清单导入系统，再进入自动筛选排序和 Word 输出流程。",
        )
    )
    keyword_rows = [
        {"类型": "精准词", "关键词": "；".join(search.get("precise_terms", []))},
        {"类型": "放宽词", "关键词": "；".join(search.get("relaxed_terms", []))},
        {"类型": "替代词", "关键词": "；".join(search.get("alternative_terms", []))},
        {"类型": "排除词", "关键词": "；".join(search.get("excluded_terms", []))},
    ]
    st.dataframe(keyword_rows, hide_index=True, use_container_width=True)
    col1, col2 = st.columns(2)
    col1.write(f"淘宝搜索关键词：{search.get('taobao_keyword', '办公屏风 工位')}")
    col1.markdown(f"[打开淘宝搜索]({search.get('taobao_search_url', 'https://s.taobao.com/search?q=%E5%8A%9E%E5%85%AC%E5%B1%8F%E9%A3%8E%20%E5%B7%A5%E4%BD%8D')})")
    col2.write(f"京东搜索关键词：{search.get('jd_keyword', '办公屏风 工位')}")
    col2.markdown(f"[打开京东搜索]({search.get('jd_search_url', 'https://search.jd.com/Search?keyword=%E5%8A%9E%E5%85%AC%E5%B1%8F%E9%A3%8E%20%E5%B7%A5%E4%BD%8D&enc=utf-8')})")

    suggestions = search.get("filter_suggestions", [])
    if suggestions:
        st.markdown("**平台筛选建议（采购辅助）**")
        st.dataframe(suggestions, hide_index=True, use_container_width=True)


def _render_stage14_v2a_mvp(st: Any) -> None:
    st.header("V2-A+ 智能寻源助手")
    _render_marketplace_search(st)

    if not hasattr(st, "file_uploader"):
        st.caption("当前运行环境不支持文件上传控件，已跳过 V2-A 上传控件渲染。")
        return

    word_upload = st.file_uploader("上传采购 Word（docx）", type=["docx"], key="stage13_2b_word_upload")
    candidate_upload = st.file_uploader(
        "上传候选商品文件（json/csv）或候选链接/混合文本清单（txt）",
        type=["json", "csv", "txt"],
        key="stage13_2b_candidate_upload",
    )

    if st.button("生成推荐 Word 与 CSV 评分表", use_container_width=True, key="stage13_2b_generate_word"):
        if word_upload is None or candidate_upload is None:
            st.warning("请先上传采购 Word 和候选商品 JSON/CSV 或候选链接/混合文本清单 TXT。")
        else:
            try:
                word_path = _save_uploaded_file(word_upload)
                candidate_path = _save_uploaded_file(candidate_upload)
                result = run_stage15_smart_sourcing_action(word_path, candidate_path)
            except Exception as exc:
                result = OperationResult(
                    name="V2-A+ 智能寻源助手",
                    success=False,
                    summary="操作未完成。",
                    output_paths=[],
                    error=str(exc),
                )
            st.session_state[STAGE15_SESSION_RESULT_KEY] = asdict(result)

    saved_result = st.session_state.get(STAGE15_SESSION_RESULT_KEY) or st.session_state.get(STAGE13_2B_SESSION_RESULT_KEY)
    if not saved_result:
        return

    result = OperationResult(**saved_result)
    _render_result(st, result)
    details = result.details or {}
    metrics = st.columns(4)
    metrics[0].metric("需求数量", details.get("requirements_count", 0))
    metrics[1].metric("候选商品数量", details.get("products_count", 0))
    metrics[2].metric("Top 推荐数量", details.get("top_products_count", 0))
    metrics[3].metric("输出 Word", _relative_path(details.get("output_docx_path", "")) if details.get("output_docx_path") else "未生成")

    if isinstance(details.get("marketplace_search"), dict):
        _render_marketplace_search(st, details["marketplace_search"])

    top_products = details.get("top_products")
    if isinstance(top_products, list) and top_products:
        rows = []
        for rank, product in enumerate(top_products, start=1):
            if not isinstance(product, dict):
                continue
            rows.append(
                {
                    "排名": rank,
                    "商品名称": product.get("title", "待人工复核"),
                    "平台": product.get("platform") or product.get("source") or "待人工复核",
                    "价格": product.get("price", "待人工复核"),
                    "尺寸": product.get("dimensions") or "待人工复核",
                    "材质": product.get("material") or "待人工复核",
                    "安装服务": product.get("installation_service") or product.get("service_text") or "待人工复核",
                    "商品链接": product.get("url") or "待人工复核",
                    "图片链接": product.get("image_url") or "待人工复核",
                    "匹配分数": product.get("score", 0),
                    "命中指标": "；".join(product.get("matched_indicators", [])) if isinstance(product.get("matched_indicators"), list) else "",
                    "待复核字段": "；".join(product.get("missing_fields", [])) if isinstance(product.get("missing_fields"), list) else "",
                    "风险提示": "；".join(product.get("risk_tips", [])) if isinstance(product.get("risk_tips"), list) else "",
                    "推荐等级": product.get("recommendation_level", "待人工复核"),
                }
            )
        if rows:
            st.subheader("Top 推荐商品")
            st.dataframe(rows, hide_index=True, use_container_width=True)
            st.subheader("人工确认问题")
            for rank, product in enumerate(top_products, start=1):
                if not isinstance(product, dict):
                    continue
                title = product.get("title") or f"候选商品 {rank}"
                with st.expander(f"第 {rank} 款：{title}"):
                    explanation = product.get("recommendation_explanation")
                    if isinstance(explanation, dict):
                        st.markdown("**推荐解释**")
                        st.json(explanation)
                    questions = product.get("manual_confirmation_questions")
                    if isinstance(questions, list) and questions:
                        st.markdown("**确认问题**")
                        for question in questions:
                            st.write(f"- {question}")

    output_docx = Path(details.get("output_docx_path", ""))
    if result.success and details.get("output_docx_path") and output_docx.exists():
        st.download_button(
            "下载推荐 Word",
            data=output_docx.read_bytes(),
            file_name=output_docx.name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True,
        )
    for label, key in [
        ("下载候选商品 JSON", "imported_candidate_products_path"),
        ("下载排序结果 JSON", "ranked_products_path"),
        ("下载 CSV 评分表", "scoring_csv_path"),
    ]:
        output_path_text = details.get(key)
        output_path = Path(output_path_text or "")
        if result.success and output_path_text and output_path.exists():
            mime = "text/csv" if key == "scoring_csv_path" else "application/json"
            st.download_button(
                label,
                data=output_path.read_bytes(),
                file_name=output_path.name,
                mime=mime,
                use_container_width=True,
                key=f"download_{key}",
            )


def _render_stage13_2b_mvp(st: Any) -> None:
    _render_stage14_v2a_mvp(st)


def render_app(st: Any | None = None) -> None:
    st = st or _load_streamlit()
    st.set_page_config(page_title="采购商品推荐与Word自动填充系统", layout="wide")

    st.title("采购商品推荐与Word自动填充系统")

    with st.sidebar:
        st.subheader("阶段状态")
        st.write("阶段12：简单操作界面")
        st.info("本系统输出为采购辅助候选，需人工复核，不代表最终采购结论。")

    st.header("项目当前状态")
    st.caption(f"项目路径：{BASE_DIR}")

    st.subheader("当前主要输入路径")
    st.table(_main_input_rows())

    st.subheader("操作")
    row1 = st.columns(3)
    row2 = st.columns(2)

    if row1[0].button("运行公开URL采集", use_container_width=True):
        st.session_state[SESSION_RESULT_KEY] = asdict(_capture_action("运行公开URL采集", run_crawler_action))
    if row1[1].button("运行主推荐流程", use_container_width=True):
        st.session_state[SESSION_RESULT_KEY] = asdict(_capture_action("运行主推荐流程", run_main_pipeline_action))
    if row1[2].button("生成复核填写模板", use_container_width=True):
        st.session_state[SESSION_RESULT_KEY] = asdict(_capture_action("生成复核填写模板", generate_review_template_action))
    if row2[0].button("校验复核填写文件", use_container_width=True):
        st.session_state[SESSION_RESULT_KEY] = asdict(_capture_action("校验复核填写文件", validate_review_filled_action))
    if row2[1].button("执行复核回填", use_container_width=True):
        st.session_state[SESSION_RESULT_KEY] = asdict(_capture_action("执行复核回填", apply_review_action))

    saved_result = st.session_state.get(SESSION_RESULT_KEY)
    if saved_result:
        _render_result(st, OperationResult(**saved_result))

    _render_stage13_2b_mvp(st)

    st.subheader("关键文件存在状态")
    st.dataframe(_file_status_rows(), hide_index=True, use_container_width=True)


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
