import csv
import importlib
import sys
import types
import unittest
from pathlib import Path

from main import build_marketplace_search_links, load_candidate_links_file, run_stage15_smart_sourcing_delivery
from src.product_ranker import rank_products
from src.sourcing_assistant import (
    build_manual_confirmation_questions,
    enrich_ranked_products_with_sourcing_guidance,
    generate_platform_filter_suggestions,
    generate_sourcing_keywords,
    parse_candidate_mixed_text,
    write_scoring_csv,
)


ROOT = Path(__file__).resolve().parents[1]
DEMO_WORD = ROOT / "data" / "办公屏风01模板样例.docx"
DEMO_MIXED_TEXT = ROOT / "data" / "stage15_candidate_mixed_text_demo.txt"

REQUIREMENTS = [
    {"name": "尺寸要求（长×宽×高）", "required_value": "1600×750×750mm"},
    {"name": "主体材质", "required_value": "钢制框架 + 实木颗粒板面板"},
    {"name": "配送及安装要求", "required_value": "配送至指定地点，包安装"},
]


class _StreamlitTrap(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.accessed: list[str] = []

    def __getattr__(self, name: str) -> object:
        self.accessed.append(name)
        raise AssertionError(f"streamlit.{name} should not be accessed during import")


def _workspace(name: str) -> Path:
    path = ROOT / "outputs" / "stage15_test_workspace" / name
    path.mkdir(parents=True, exist_ok=True)
    return path


class Stage15SmartSourcingAssistantTests(unittest.TestCase):
    def test_generate_precise_relaxed_alternative_and_excluded_keywords(self) -> None:
        keywords = generate_sourcing_keywords(REQUIREMENTS)

        self.assertIn("precise_terms", keywords)
        self.assertIn("relaxed_terms", keywords)
        self.assertIn("alternative_terms", keywords)
        self.assertIn("excluded_terms", keywords)
        self.assertIn("办公屏风", keywords["precise_terms"][0])
        self.assertIn("1600x750x750", keywords["precise_terms"][0])
        self.assertIn("钢制", keywords["precise_terms"][0])
        self.assertIn("安装", keywords["precise_terms"][0])
        self.assertTrue(any("办公桌屏风组合" in item for item in keywords["relaxed_terms"]))
        self.assertTrue(any("职员工位" in item for item in keywords["alternative_terms"]))
        self.assertIn("水壶", keywords["excluded_terms"])

    def test_generate_taobao_and_jd_search_links(self) -> None:
        search = build_marketplace_search_links(REQUIREMENTS)

        self.assertIn("s.taobao.com/search", search["taobao_search_url"])
        self.assertIn("search.jd.com/Search", search["jd_search_url"])
        self.assertIn("taobao_keyword", search)
        self.assertIn("jd_keyword", search)
        self.assertIn("不强抓", search["notice"])

    def test_generate_platform_filter_suggestions(self) -> None:
        suggestions = generate_platform_filter_suggestions(REQUIREMENTS)
        text = "\n".join(f"{item['category']} {item['suggestion']}" for item in suggestions)

        for keyword in ["价格区间", "企业店", "发票", "配送", "同城", "规格完整性", "售后", "截图"]:
            self.assertIn(keyword, text)
        self.assertIn("采购辅助", text)

    def test_parse_mixed_text_extracts_link_platform_price_size_material_and_installation(self) -> None:
        products = parse_candidate_mixed_text(DEMO_MIXED_TEXT.read_text(encoding="utf-8"))

        self.assertEqual(len(products), 4)
        self.assertEqual(products[0]["platform"], "淘宝")
        self.assertEqual(products[0]["price"], 998)
        self.assertIn("1600x750x750", products[0]["dimensions"])
        self.assertIn("钢制", products[0]["material"])
        self.assertIn("安装", products[0]["installation_service"])
        self.assertEqual(products[1]["platform"], "京东")
        self.assertEqual(products[2]["platform"], "天猫")
        self.assertIn("客户在候选链接/文本", products[0]["evidence_text"])

    def test_plain_link_is_pending_manual_review_without_fabricated_fields(self) -> None:
        products = parse_candidate_mixed_text(DEMO_MIXED_TEXT.read_text(encoding="utf-8"))
        plain_link = products[-1]

        self.assertTrue(plain_link["title"].startswith("待人工复核候选商品"))
        self.assertIsNone(plain_link["price"])
        self.assertEqual(plain_link["dimensions"], "")
        self.assertEqual(plain_link["material"], "")
        self.assertIn("title", plain_link["missing_fields"])
        self.assertIn("price", plain_link["missing_fields"])
        self.assertIn("dimensions", plain_link["missing_fields"])
        self.assertIn("material", plain_link["missing_fields"])
        self.assertTrue(plain_link["manual_review_required"])

    def test_stage14_txt_loader_accepts_stage15_mixed_text_shape(self) -> None:
        products = load_candidate_links_file(DEMO_MIXED_TEXT)

        self.assertEqual(len(products), 4)
        self.assertEqual(products[0]["adapter_source_type"], "manual_link_list")
        self.assertIn("安装", products[0]["installation_service"])
        self.assertIn("image_url", products[0]["missing_fields"])

    def test_manual_confirmation_questions_are_generated(self) -> None:
        product = parse_candidate_mixed_text(DEMO_MIXED_TEXT.read_text(encoding="utf-8"))[0]
        questions = build_manual_confirmation_questions(product, REQUIREMENTS)
        joined = "\n".join(questions)

        self.assertGreaterEqual(len(questions), 7)
        self.assertIn("运费", joined)
        self.assertIn("尺寸", joined)
        self.assertIn("材质", joined)
        self.assertIn("配送", joined)
        self.assertIn("截图", joined)
        self.assertIn("继续补充字段", joined)

    def test_recommendation_explanation_fields_are_added_without_rewriting_ranker(self) -> None:
        products = parse_candidate_mixed_text(DEMO_MIXED_TEXT.read_text(encoding="utf-8"))
        products.append(
            {
                "title": "家用电热水壶",
                "platform": "客户候选",
                "price": 99,
                "url": "https://example.com/kettle",
                "raw_text": "家用电热水壶 99元",
            }
        )
        ranked = rank_products(products, REQUIREMENTS)
        enriched = enrich_ranked_products_with_sourcing_guidance(ranked, REQUIREMENTS)

        first = enriched[0]
        self.assertIn("recommendation_explanation", first)
        for key in [
            "why_recommended",
            "matched_requirements",
            "pending_review_fields",
            "main_risks",
            "lower_rank_reason",
            "exclusion_reason",
        ]:
            self.assertIn(key, first["recommendation_explanation"])
        self.assertIn("manual_confirmation_questions", first)
        water = next(item for item in enriched if "水壶" in item["title"])
        self.assertIn("明显无关", water["exclusion_reason"])

    def test_scoring_csv_is_written_with_required_columns(self) -> None:
        workspace = _workspace("scoring_csv")
        products = parse_candidate_mixed_text(DEMO_MIXED_TEXT.read_text(encoding="utf-8"))
        ranked = enrich_ranked_products_with_sourcing_guidance(rank_products(products, REQUIREMENTS), REQUIREMENTS)
        output_path = write_scoring_csv(ranked, workspace / "score.csv")

        self.assertTrue(output_path.exists())
        with output_path.open("r", encoding="utf-8-sig", newline="") as file_obj:
            reader = csv.DictReader(file_obj)
            rows = list(reader)

        self.assertGreaterEqual(len(rows), 4)
        for field in ["排名", "商品名称", "平台", "价格", "尺寸", "材质", "安装服务", "商品链接", "图片链接", "匹配分数", "命中指标", "待复核字段", "风险提示", "人工确认问题", "推荐等级"]:
            self.assertIn(field, reader.fieldnames or [])

    def test_stage15_delivery_generates_word_json_and_scoring_csv(self) -> None:
        workspace = _workspace("delivery")
        result = run_stage15_smart_sourcing_delivery(DEMO_WORD, DEMO_MIXED_TEXT, output_dir=workspace)

        self.assertEqual(result["products_count"], 4)
        self.assertTrue(Path(result["output_docx_path"]).exists())
        self.assertTrue(Path(result["imported_candidate_products_path"]).exists())
        self.assertTrue(Path(result["ranked_products_path"]).exists())
        self.assertTrue(Path(result["scoring_csv_path"]).exists())
        self.assertIn("platform_filter_suggestions", result)
        self.assertIn("sourcing_keywords", result)

    def test_ui_streamlit_imports_without_streamlit_side_effects(self) -> None:
        previous_streamlit = sys.modules.get("streamlit")
        trap = _StreamlitTrap()
        sys.modules["streamlit"] = trap
        sys.modules.pop("ui_streamlit", None)

        try:
            module = importlib.import_module("ui_streamlit")
        finally:
            if previous_streamlit is None:
                sys.modules.pop("streamlit", None)
            else:
                sys.modules["streamlit"] = previous_streamlit

        self.assertTrue(callable(getattr(module, "render_app", None)))
        self.assertTrue(callable(getattr(module, "run_stage15_smart_sourcing_action", None)))
        self.assertEqual(trap.accessed, [])

    def test_no_disallowed_implementation_markers(self) -> None:
        checked_files = [
            ROOT / "main.py",
            ROOT / "ui_streamlit.py",
            ROOT / "src" / "doc_writer.py",
            ROOT / "src" / "sourcing_assistant.py",
        ]
        combined_text = "\n".join(path.read_text(encoding="utf-8") for path in checked_files)

        for phrase in ["本报告为最终采购结论", "可直接下单", "保存 Cookie", "绕过验证码", "使用代理池"]:
            self.assertNotIn(phrase, combined_text)


if __name__ == "__main__":
    unittest.main()
