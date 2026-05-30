import unittest
from pathlib import Path

from main import run_pipeline
from src.doc_parser import parse_requirements
from src.doc_writer import write_responses
from src.product_loader import load_products, load_products_json, normalize_products, validate_product
from src.product_ranker import rank_products
from src.response_builder import build_recommendation_responses, select_top_products


class Stage57Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.word_path = self.root / "data" / "办公屏风01模板样例.docx"
        self.sample_products_path = self.root / "data" / "sample_products.json"
        self.requirements = parse_requirements(self.word_path)

    def test_product_loader_reads_sample_products(self) -> None:
        products = load_products_json(self.sample_products_path)

        self.assertGreaterEqual(len(products), 1)
        self.assertIn("product_id", products[0])
        self.assertIn("source", products[0])

    def test_normalize_products_handles_missing_fields(self) -> None:
        products = normalize_products([{"title": "只含标题的本地测试商品"}])

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["price"], None)
        self.assertEqual(products[0]["title"], "只含标题的本地测试商品")
        self.assertTrue(validate_product(products[0]))

    def test_rank_products_returns_ranked_list(self) -> None:
        products = load_products_json(self.sample_products_path)
        ranked_products = rank_products(products, self.requirements)

        self.assertGreaterEqual(len(ranked_products), 1)
        self.assertGreaterEqual(ranked_products[0]["score"], ranked_products[-1]["score"])
        self.assertIn("reasons", ranked_products[0])
        self.assertIn("risks", ranked_products[0])
        self.assertIn("score_detail", ranked_products[0])

    def test_response_builder_accepts_ranked_products(self) -> None:
        products = load_products_json(self.sample_products_path)
        ranked_products = rank_products(products, self.requirements)
        top_products = select_top_products(ranked_products, top_n=3)
        responses = build_recommendation_responses(self.requirements, ranked_products, top_n=3)

        self.assertEqual(len(top_products), 3)
        self.assertEqual(len(responses), len(self.requirements))

    def test_main_pipeline_runs_end_to_end(self) -> None:
        result = run_pipeline()

        self.assertEqual(result["requirements_count"], len(self.requirements))
        self.assertEqual(result["top_products_count"], 3)
        self.assertTrue(Path(result["ranked_products_path"]).exists())
        self.assertTrue(Path(result["responses_path"]).exists())
        self.assertTrue(Path(result["output_docx_path"]).exists())

    def test_legacy_imports_are_available(self) -> None:
        self.assertTrue(callable(load_products))
        self.assertTrue(callable(rank_products))
        self.assertTrue(callable(write_responses))


if __name__ == "__main__":
    unittest.main()
