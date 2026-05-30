import json
import unittest
from pathlib import Path

from main import _select_products_json_path
from src.crawler.review_apply import apply_manual_reviews, load_review_filled


class Stage10ReviewApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.workspace = self.root / "outputs" / "stage10_test_workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def _write_json(self, name: str, data: object) -> Path:
        path = self.workspace / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def _apply(self, products: list[dict[str, object]], review_items: object) -> tuple[list[dict[str, object]], dict[str, object]]:
        products_path = self._write_json("products.json", products)
        review_path = self._write_json("manual_review_filled.json", review_items)
        output_products_path = self.workspace / "reviewed_products.json"
        output_report_path = self.workspace / "review_report.json"

        report = apply_manual_reviews(products_path, review_path, output_products_path, output_report_path)
        reviewed_products = json.loads(output_products_path.read_text(encoding="utf-8"))
        saved_report = json.loads(output_report_path.read_text(encoding="utf-8"))

        self.assertEqual(report, saved_report)
        return reviewed_products, saved_report

    def test_load_review_filled_accepts_top_level_array(self) -> None:
        review_path = self._write_json("review_array.json", [{"title": "A", "review_status": "approved"}])

        review_items = load_review_filled(review_path)

        self.assertEqual(len(review_items), 1)
        self.assertEqual(review_items[0]["title"], "A")

    def test_load_review_filled_accepts_object_review_items(self) -> None:
        review_path = self._write_json("review_object.json", {"review_items": [{"title": "B", "review_status": "approved"}]})

        review_items = load_review_filled(review_path)

        self.assertEqual(len(review_items), 1)
        self.assertEqual(review_items[0]["title"], "B")

    def test_approved_matches_by_url_and_updates_only_confirmed_fields(self) -> None:
        reviewed_products, report = self._apply(
            [
                {
                    "title": "URL 匹配办公屏风",
                    "url": "https://example.com/product-a",
                    "source": "客户公开资料",
                    "price": None,
                    "dimensions": "",
                    "material": "",
                    "service_text": "",
                    "evidence_text": "",
                    "notes": "保留旧备注",
                }
            ],
            [
                {
                    "title": "URL 匹配办公屏风",
                    "url": "https://example.com/product-a",
                    "source": "客户公开资料",
                    "review_status": "approved",
                    "review_note": "客户已核对页面参数。",
                    "confirmed_price": 899,
                    "confirmed_dimensions": "1600x750x750mm",
                    "confirmed_material": "钢制框架，颗粒板",
                    "confirmed_installation_service": "支持配送和现场安装。",
                    "confirmed_evidence_text": "客户公开资料页面显示价格、尺寸、材质和现场安装服务。",
                    "confirmed_fields": ["price", "dimensions"],
                }
            ],
        )

        self.assertEqual(len(reviewed_products), 1)
        product = reviewed_products[0]
        self.assertEqual(product["price"], 899)
        self.assertEqual(product["dimensions"], "1600x750x750mm")
        self.assertEqual(product["material"], "钢制框架，颗粒板")
        self.assertEqual(product["service_text"], "支持配送和现场安装。")
        self.assertEqual(product["evidence_text"], "客户公开资料页面显示价格、尺寸、材质和现场安装服务。")
        self.assertEqual(product["evidence"], "客户公开资料页面显示价格、尺寸、材质和现场安装服务。")
        self.assertEqual(product["notes"], "保留旧备注")
        self.assertEqual(product["review_note"], "客户已核对页面参数。")
        self.assertFalse(product["manual_review_required"])
        self.assertEqual(product["remaining_missing_fields"], [])
        self.assertIn("installation_service", product["reviewed_fields"])
        self.assertEqual(report["approved_count"], 1)
        self.assertGreaterEqual(report["field_updates_count"], 6)

    def test_rejected_does_not_enter_reviewed_products(self) -> None:
        reviewed_products, report = self._apply(
            [{"title": "驳回商品", "url": "https://example.com/rejected", "source": "客户资料"}],
            [{"title": "驳回商品", "url": "https://example.com/rejected", "review_status": "rejected", "review_note": "价格不合适"}],
        )

        self.assertEqual(reviewed_products, [])
        self.assertEqual(report["rejected_count"], 1)
        self.assertEqual(len(report["rejected_items"]), 1)

    def test_needs_more_info_enters_unresolved_items(self) -> None:
        reviewed_products, report = self._apply(
            [{"title": "待补商品", "url": "https://example.com/unresolved", "source": "客户资料"}],
            [
                {
                    "title": "待补商品",
                    "url": "https://example.com/unresolved",
                    "review_status": "needs_more_info",
                    "review_note": "还缺安装服务说明",
                }
            ],
        )

        self.assertEqual(reviewed_products, [])
        self.assertEqual(report["needs_more_info_count"], 1)
        self.assertEqual(len(report["unresolved_items"]), 1)

    def test_empty_url_matches_by_title_and_source(self) -> None:
        reviewed_products, report = self._apply(
            [{"title": "弱匹配办公屏风", "url": "", "source": "客户 CSV", "price": None}],
            [
                {
                    "title": "弱匹配办公屏风",
                    "url": "",
                    "source": "客户 CSV",
                    "review_status": "approved",
                    "confirmed_price": 1000,
                }
            ],
        )

        self.assertEqual(len(reviewed_products), 1)
        self.assertEqual(reviewed_products[0]["price"], 1000)
        self.assertEqual(report["unmatched_review_items"], [])

    def test_unmatched_review_item_is_reported_without_crash(self) -> None:
        reviewed_products, report = self._apply(
            [{"title": "已有商品", "url": "https://example.com/existing", "source": "客户资料"}],
            [{"title": "未知商品", "url": "https://example.com/missing", "review_status": "approved", "confirmed_price": 1}],
        )

        self.assertEqual(reviewed_products, [])
        self.assertEqual(len(report["unmatched_review_items"]), 1)
        self.assertEqual(report["reviewed_products_count"], 0)

    def test_approved_product_still_requires_review_when_key_fields_remain_missing(self) -> None:
        reviewed_products, _report = self._apply(
            [{"title": "仍缺字段办公屏风", "url": "https://example.com/partial", "source": "客户资料"}],
            [{"title": "仍缺字段办公屏风", "url": "https://example.com/partial", "review_status": "approved", "confirmed_price": 688}],
        )

        self.assertEqual(len(reviewed_products), 1)
        product = reviewed_products[0]
        self.assertTrue(product["manual_review_required"])
        self.assertIn("dimensions", product["remaining_missing_fields"])
        self.assertIn("material", product["remaining_missing_fields"])
        self.assertIn("installation_service", product["remaining_missing_fields"])

    def test_fully_reviewed_product_clears_manual_review_required(self) -> None:
        reviewed_products, _report = self._apply(
            [{"title": "完整回填办公屏风", "url": "https://example.com/full", "source": ""}],
            [
                {
                    "title": "完整回填办公屏风",
                    "url": "https://example.com/full",
                    "review_status": "approved",
                    "confirmed_price": 1280,
                    "confirmed_dimensions": "1600x750x750mm",
                    "confirmed_material": "钢制框架，颗粒板",
                    "confirmed_installation_service": "支持现场安装。",
                    "confirmed_source": "客户人工复核资料",
                    "confirmed_evidence_text": "客户人工复核资料确认价格、尺寸、材质、来源和现场安装服务。",
                }
            ],
        )

        self.assertEqual(len(reviewed_products), 1)
        self.assertFalse(reviewed_products[0]["manual_review_required"])
        self.assertEqual(reviewed_products[0]["remaining_missing_fields"], [])

    def test_main_selects_reviewed_products_first_and_falls_back_when_invalid(self) -> None:
        reviewed_path = self._write_json("main_reviewed_products.json", [{"title": "已复核办公屏风", "review_status": "approved"}])
        crawler_path = self._write_json("main_crawler_products.json", [{"title": "采集办公屏风", "url": "https://example.com/crawler"}])
        fallback_path = self.root / "data" / "sample_products.json"

        selected = _select_products_json_path(crawler_path, fallback_path, reviewed_products_path=reviewed_path)
        self.assertEqual(selected, reviewed_path)

        reviewed_path.write_text("[]", encoding="utf-8")
        selected = _select_products_json_path(crawler_path, fallback_path, reviewed_products_path=reviewed_path)
        self.assertEqual(selected, crawler_path)

        crawler_path.write_text("[]", encoding="utf-8")
        selected = _select_products_json_path(crawler_path, fallback_path, reviewed_products_path=reviewed_path)
        self.assertEqual(selected, fallback_path)


if __name__ == "__main__":
    unittest.main()
