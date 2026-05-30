from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from main import run_pipeline
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

    st.subheader("关键文件存在状态")
    st.dataframe(_file_status_rows(), hide_index=True, use_container_width=True)


def main() -> None:
    render_app()


if __name__ == "__main__":
    main()
