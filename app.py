import hashlib
from pathlib import Path

import streamlit as st

from src.doc_parser import parse_requirements, save_requirements_json
from src.doc_writer import write_responses
from src.product_loader import load_products
from src.product_ranker import rank_products, save_ranked_products_json
from src.response_builder import (
    build_recommendation_responses,
    save_responses_json,
    select_top_products,
)


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PRODUCTS_JSON = BASE_DIR / "data" / "products.json"
INPUT_DOCX = OUTPUT_DIR / "input.docx"
REQUIREMENTS_JSON = OUTPUT_DIR / "requirements.json"
OUTPUT_DOCX = OUTPUT_DIR / "output.docx"
RANKED_PRODUCTS_JSON = OUTPUT_DIR / "ranked_products.json"
RESPONSES_JSON = OUTPUT_DIR / "responses.json"
PRODUCT_DISPLAY_FIELDS = ["title", "platform", "price", "shop", "url", "specs_text", "service_text"]
RANKED_DISPLAY_FIELDS = ["score", "title", "platform", "price", "shop", "url", "reasons", "risks"]


def save_uploaded_file(file_bytes: bytes, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(file_bytes)


st.set_page_config(page_title="Word 闭环", layout="wide")

st.title("阶段 1：Word 输入输出闭环")
st.caption("上传 Word，解析技术参数表，生成模拟响应并写回 Word。")

for key, value in {
    "current_upload_key": None,
    "output_generated": False,
    "output_upload_key": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value

requirements = None
requirements_valid = False
current_upload_key = None
ranked_products = []
ranked_products_valid = False
uploaded_file = st.file_uploader("上传采购技术规范 Word 文档", type=["docx"])

if uploaded_file is not None:
    uploaded_bytes = uploaded_file.getvalue()
    current_upload_key = hashlib.sha256(uploaded_bytes).hexdigest()
    if st.session_state.current_upload_key != current_upload_key:
        st.session_state.current_upload_key = current_upload_key
        st.session_state.output_generated = False
        st.session_state.output_upload_key = None

    try:
        save_uploaded_file(uploaded_bytes, INPUT_DOCX)
        requirements = parse_requirements(INPUT_DOCX)
        requirements_valid = isinstance(requirements, list) and len(requirements) > 0

        if requirements_valid:
            save_requirements_json(requirements, REQUIREMENTS_JSON)

            st.success(f"已解析 {len(requirements)} 条技术参数。")
            st.dataframe(requirements, use_container_width=True)
        else:
            st.warning("未解析到有效技术参数，请检查上传的 Word 文档。")
    except Exception as exc:
        st.error(f"处理失败：{exc}")
else:
    if st.session_state.current_upload_key is not None:
        st.session_state.current_upload_key = None
        st.session_state.output_generated = False
        st.session_state.output_upload_key = None
    st.info("请选择 .docx 文件开始。")

st.divider()
st.subheader("本地候选商品")
st.caption("读取 data/products.json 中的本地样例商品。")

products = []
products_load_error = None
products_loaded = False
try:
    products = load_products(PRODUCTS_JSON)
    products_loaded = isinstance(products, list) and len(products) > 0
    if products_loaded:
        product_rows = [{field: product.get(field) for field in PRODUCT_DISPLAY_FIELDS} for product in products]
        st.success(f"已加载 {len(products)} 条候选商品。")
        st.dataframe(
            product_rows,
            use_container_width=True,
            column_config={"url": st.column_config.LinkColumn("url")},
        )
    else:
        st.warning("未读取到有效候选商品。")
except Exception as exc:
    products_load_error = exc
    st.error(f"本地候选商品读取失败：{exc}")

st.divider()
st.subheader("规则排序结果")
st.caption("本地规则匹配结果")

if uploaded_file is None:
    st.info("上传 Word 后可生成规则排序结果。")
elif not requirements_valid:
    st.warning("未解析到有效技术参数，暂不能生成规则排序结果。")
elif products_load_error is not None:
    st.error(f"本地规则匹配结果失败：{products_load_error}")
elif not products_loaded:
    st.warning("未读取到有效候选商品，暂不能生成规则排序结果。")
else:
    try:
        ranked_products = rank_products(products, requirements)
        save_ranked_products_json(ranked_products, RANKED_PRODUCTS_JSON)
        ranked_products_valid = isinstance(ranked_products, list) and len(ranked_products) > 0
        ranked_rows = []
        for product in ranked_products:
            row = {field: product.get(field) for field in RANKED_DISPLAY_FIELDS}
            row["reasons"] = "；".join(product.get("reasons", []))
            row["risks"] = "；".join(product.get("risks", []))
            ranked_rows.append(row)

        st.success(f"候选商品排序：{len(ranked_products)} 条。")
        st.dataframe(
            ranked_rows,
            use_container_width=True,
            column_config={"url": st.column_config.LinkColumn("url")},
        )
    except Exception as exc:
        st.error(f"本地规则匹配结果失败：{exc}")

st.divider()
st.subheader("规则响应与 Word 导出")
st.caption("基于当前页面规则排序结果生成响应，Top 1 用于逐项参数响应，Top 2 和 Top 3 仅写入候选商品汇总表。")

if uploaded_file is None:
    st.info("上传 Word 后可生成规则响应并导出 Word。")
elif not requirements_valid:
    st.warning("未解析到有效技术参数，暂不能生成 Word。")
elif products_load_error is not None:
    st.error(f"本地候选商品读取失败，暂不能生成 Word：{products_load_error}")
elif not products_loaded:
    st.warning("未读取到有效候选商品，暂不能生成 Word。")
elif not ranked_products_valid:
    st.warning("当前排序结果为空，暂不能生成 Word。")
else:
    if st.button("生成规则响应并导出 Word", type="primary"):
        st.session_state.output_generated = False
        st.session_state.output_upload_key = None
        top_products = select_top_products(ranked_products, top_n=3)

        if not top_products:
            st.error("没有可用候选商品，暂不能生成 Word。")
        else:
            try:
                responses = build_recommendation_responses(requirements, ranked_products, top_n=3)
                save_responses_json(responses, RESPONSES_JSON)
                write_responses(INPUT_DOCX, responses, OUTPUT_DOCX, summary_products=top_products)
                st.session_state.output_generated = True
                st.session_state.output_upload_key = current_upload_key
                st.success("已生成规则响应和输出 Word。")
            except Exception as exc:
                st.error(f"生成 Word 失败：{exc}")

can_download_output = (
    uploaded_file is not None
    and st.session_state.output_generated
    and st.session_state.output_upload_key == current_upload_key
    and OUTPUT_DOCX.exists()
)
if can_download_output:
    try:
        output_bytes = OUTPUT_DOCX.read_bytes()
    except Exception as exc:
        st.error(f"读取 output.docx 失败：{exc}")
    else:
        st.download_button(
            label="下载 output.docx",
            data=output_bytes,
            file_name="output.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
