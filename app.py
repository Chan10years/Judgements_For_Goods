from pathlib import Path

import streamlit as st

from src.doc_parser import parse_requirements, save_requirements_json
from src.doc_writer import write_responses
from src.mock_response import build_mock_responses
from src.product_loader import load_products


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
PRODUCTS_JSON = BASE_DIR / "data" / "products.json"
INPUT_DOCX = OUTPUT_DIR / "input.docx"
REQUIREMENTS_JSON = OUTPUT_DIR / "requirements.json"
OUTPUT_DOCX = OUTPUT_DIR / "output.docx"
PRODUCT_DISPLAY_FIELDS = ["title", "platform", "price", "shop", "url", "specs_text", "service_text"]


def save_uploaded_file(uploaded_file, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(uploaded_file.getbuffer())


st.set_page_config(page_title="Word 闭环", layout="wide")

st.title("阶段 1：Word 输入输出闭环")
st.caption("上传 Word，解析技术参数表，生成模拟响应并写回 Word。")

uploaded_file = st.file_uploader("上传采购技术规范 Word 文档", type=["docx"])

if uploaded_file is not None:
    try:
        save_uploaded_file(uploaded_file, INPUT_DOCX)
        requirements = parse_requirements(INPUT_DOCX)
        save_requirements_json(requirements, REQUIREMENTS_JSON)

        st.success(f"已解析 {len(requirements)} 条技术参数。")
        st.dataframe(requirements, use_container_width=True)

        if st.button("生成模拟响应并导出 Word", type="primary"):
            responses = build_mock_responses(requirements)
            write_responses(INPUT_DOCX, responses, OUTPUT_DOCX)
            st.success("已生成输出 Word。")

        if OUTPUT_DOCX.exists():
            st.download_button(
                label="下载 output.docx",
                data=OUTPUT_DOCX.read_bytes(),
                file_name="output.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    except Exception as exc:
        st.error(f"处理失败：{exc}")
else:
    st.info("请选择 .docx 文件开始。")

st.divider()
st.subheader("本地候选商品")
st.caption("读取 data/products.json 中的本地样例商品。")

try:
    products = load_products(PRODUCTS_JSON)
    product_rows = [{field: product.get(field) for field in PRODUCT_DISPLAY_FIELDS} for product in products]
    st.success(f"已加载 {len(products)} 条候选商品。")
    st.dataframe(
        product_rows,
        use_container_width=True,
        column_config={"url": st.column_config.LinkColumn("url")},
    )
except Exception as exc:
    st.error(f"本地候选商品读取失败：{exc}")
