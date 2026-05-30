import csv
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from main import run_pipeline
from src.crawler.adapters.manual_csv_adapter import ManualCsvAdapter
from src.crawler.adapters.manual_json_adapter import ManualJsonAdapter
from src.crawler.adapters.static_page_adapter import StaticPageAdapter
from src.crawler.models import FetchResult, RobotsDecision
from src.crawler.review import generate_manual_review_items


class Stage9AdapterReviewTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.workspace = self.root / "outputs" / "stage9_test_workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)

    def test_manual_json_adapter_loads_customer_products(self) -> None:
        json_path = self.workspace / "manual_products.json"
        json_path.write_text(
            json.dumps(
                {
                    "products": [
                        {
                            "商品名称": "客户办公屏风工位 1600x750x750",
                            "价格": "899",
                            "规格参数": "尺寸：1600x750x750mm；材质：钢制框架，颗粒板台面。",
                            "安装服务": "支持现场安装和售后咨询。",
                            "来源": "客户提供公开资料",
                            "链接": "https://example.com/manual-json-product",
                        }
                    ]
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        products = ManualJsonAdapter(json_path).load_candidates()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["price"], 899)
        self.assertEqual(products[0]["source"], "客户提供公开资料")
        self.assertEqual(products[0]["adapter_source_type"], "manual_json")
        self.assertFalse(products[0]["manual_review_required"])

    def test_manual_json_adapter_accepts_top_level_array_and_yuan_price(self) -> None:
        json_path = self.workspace / "manual_products_array.json"
        json_path.write_text(
            json.dumps(
                [
                    {
                        "name": "客户英文映射办公屏风 1600x750x750",
                        "价格": "¥1,280",
                        "供应商": "客户供应商 A",
                        "来源": "客户 JSON",
                        "URL": "https://example.com/manual-json-array",
                        "规格": "尺寸：1600x750x750mm；材质：钢架，颗粒板。",
                        "服务": "支持配送和现场安装。",
                        "交期": "预计 7 天，作为未识别字段保留。",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        products = ManualJsonAdapter(json_path).load_candidates()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["title"], "客户英文映射办公屏风 1600x750x750")
        self.assertEqual(products[0]["price"], 1280)
        self.assertEqual(products[0]["shop"], "客户供应商 A")
        self.assertEqual(products[0]["url"], "https://example.com/manual-json-array")
        self.assertIn("交期", products[0]["extra"])
        self.assertFalse(products[0]["manual_review_required"])

    def test_manual_csv_adapter_loads_customer_products_and_marks_missing_fields(self) -> None:
        csv_path = self.workspace / "manual_products.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=["商品名称", "链接", "规格参数"])
            writer.writeheader()
            writer.writerow(
                {
                    "商品名称": "客户缺字段办公屏风",
                    "链接": "https://example.com/manual-csv-product",
                    "规格参数": "仅说明为办公屏风，价格、材质、安装服务待客户确认。",
                }
            )

        products = ManualCsvAdapter(csv_path).load_candidates()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["title"], "客户缺字段办公屏风")
        self.assertTrue(products[0]["manual_review_required"])
        self.assertIn("price", products[0]["missing_fields"])
        self.assertIn("source", products[0]["missing_fields"])

    def test_manual_csv_adapter_handles_utf8_headers_empty_fields_and_yuan_price(self) -> None:
        csv_path = self.workspace / "manual_products_utf8.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=["商品名称", "价格", "店铺", "链接", "图片链接", "参数", "安装服务", "来源", "交期"])
            writer.writeheader()
            writer.writerow(
                {
                    "商品名称": "CSV 完整办公屏风 1600x750x750",
                    "价格": "¥999",
                    "店铺": "客户店铺 A",
                    "链接": "https://example.com/manual-csv-full",
                    "图片链接": "https://example.com/image.jpg",
                    "参数": "尺寸：1600x750x750mm；材质：钢制框架，颗粒板。",
                    "安装服务": "支持现场安装。",
                    "来源": "客户 CSV",
                    "交期": "预计 5 天",
                }
            )
            file_obj.write("\n")
            writer.writerow({"价格": "¥888", "来源": "客户 CSV"})

        products = ManualCsvAdapter(csv_path, encoding="utf-8").load_candidates()
        full_product = next(product for product in products if product["title"] == "CSV 完整办公屏风 1600x750x750")
        missing_title_product = next(product for product in products if product["price"] == 888)

        self.assertEqual(full_product["price"], 999)
        self.assertEqual(full_product["shop"], "客户店铺 A")
        self.assertEqual(full_product["image_url"], "https://example.com/image.jpg")
        self.assertIn("交期", full_product["extra"])
        self.assertFalse(full_product["manual_review_required"])
        self.assertFalse(missing_title_product["parse_success"])
        self.assertTrue(missing_title_product["manual_review_required"])

    def test_static_page_adapter_reuses_stage8_public_page_pipeline(self) -> None:
        temp_root = self.workspace / "static_adapter"
        temp_root.mkdir(parents=True, exist_ok=True)
        config_path = temp_root / "crawler_config.json"
        seed_path = temp_root / "seed_urls.json"
        raw_path = temp_root / "crawler_raw.json"
        products_path = temp_root / "crawler_products.json"
        report_path = temp_root / "crawler_report.json"
        log_path = temp_root / "crawler_run.log"
        config_path.write_text(
            json.dumps(
                {
                    "user_agent": "Stage9StaticAdapterTest/1.0",
                    "timeout_seconds": 10,
                    "max_retries": 0,
                    "retry_backoff_seconds": 0,
                    "request_interval_seconds": 2,
                    "respect_robots_txt": True,
                    "max_urls_per_run": 20,
                    "output_raw_path": str(raw_path),
                    "output_products_path": str(products_path),
                    "output_report_path": str(report_path),
                    "log_path": str(log_path),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        seed_path.write_text(
            json.dumps(
                [
                    {
                        "url": "https://example.com/static-product",
                        "source_name": "ExampleStatic",
                        "category_hint": "办公家具",
                        "note": "阶段 9 静态页面适配测试",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        html = """
        <html><body>
          <h1>客户公开页办公屏风工位 1600x750x750</h1>
          <p>价格：1099</p>
          <p>规格参数：尺寸 1600x750x750mm；材质：钢制框架，颗粒板。</p>
          <p>服务：支持配送和现场安装。</p>
        </body></html>
        """

        def fake_can_fetch(self, seed):
            return RobotsDecision(seed.url, True, "robots_allowed", "https://example.com/robots.txt")

        def fake_fetch(self, seed):
            return FetchResult(
                url=seed.url,
                source_name=seed.source_name,
                ok=True,
                status_code=200,
                final_url=seed.url,
                content_type="text/html",
                text=html,
                error_type="",
                error_message="",
                attempts=1,
                elapsed_seconds=0.01,
            )

        with patch("src.crawler.robots_checker.RobotsChecker.can_fetch", fake_can_fetch), patch(
            "src.crawler.fetcher.ProductFetcher.fetch", fake_fetch
        ):
            products = StaticPageAdapter(config_path=config_path, seed_path=seed_path).load_candidates()

        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["source"], "ExampleStatic")
        self.assertEqual(products[0]["adapter_source_type"], "static_page")
        self.assertTrue(products_path.exists())
        self.assertTrue((temp_root / "manual_review_items.json").exists())

    def test_static_page_adapter_parse_failure_is_reported_without_fake_product(self) -> None:
        temp_root = self.workspace / "static_adapter_parse_failure"
        temp_root.mkdir(parents=True, exist_ok=True)
        config_path = temp_root / "crawler_config.json"
        seed_path = temp_root / "seed_urls.json"
        products_path = temp_root / "crawler_products.json"
        report_path = temp_root / "crawler_report.json"
        config_path.write_text(
            json.dumps(
                {
                    "user_agent": "Stage9StaticAdapterFailureTest/1.0",
                    "timeout_seconds": 10,
                    "max_retries": 0,
                    "retry_backoff_seconds": 0,
                    "request_interval_seconds": 2,
                    "respect_robots_txt": True,
                    "max_urls_per_run": 20,
                    "output_raw_path": str(temp_root / "crawler_raw.json"),
                    "output_products_path": str(products_path),
                    "output_report_path": str(report_path),
                    "log_path": str(temp_root / "crawler_run.log"),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        seed_path.write_text(
            json.dumps(
                [
                    {
                        "url": "https://example.com/no-title",
                        "source_name": "ExampleStatic",
                        "category_hint": "办公家具",
                        "note": "解析失败测试",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        def fake_can_fetch(self, seed):
            return RobotsDecision(seed.url, True, "robots_allowed", "https://example.com/robots.txt")

        def fake_fetch(self, seed):
            return FetchResult(
                url=seed.url,
                source_name=seed.source_name,
                ok=True,
                status_code=200,
                final_url=seed.url,
                content_type="text/html",
                text="<html><body><p>没有标题的普通正文。</p></body></html>",
                error_type="",
                error_message="",
                attempts=1,
                elapsed_seconds=0.01,
            )

        with patch("src.crawler.robots_checker.RobotsChecker.can_fetch", fake_can_fetch), patch(
            "src.crawler.fetcher.ProductFetcher.fetch", fake_fetch
        ):
            products = StaticPageAdapter(config_path=config_path, seed_path=seed_path).load_candidates()

        report = json.loads(report_path.read_text(encoding="utf-8"))
        saved_products = json.loads(products_path.read_text(encoding="utf-8"))

        self.assertEqual(products, [])
        self.assertEqual(saved_products, [])
        self.assertEqual(report["parse_failure_count"], 1)
        self.assertEqual(report["summary"]["失败 URL 数"], 1)

    def test_review_generates_manual_review_items_for_missing_fields(self) -> None:
        review_path = self.workspace / "manual_review_items.json"
        products = [
            {
                "title": "缺字段办公屏风",
                "url": "https://example.com/missing-fields",
                "source": "",
                "price": None,
                "specs_text": "仅有标题和极少规格。",
                "service_text": "",
                "raw_text": "短",
            }
        ]

        review_items = generate_manual_review_items(products, review_path)
        saved_items = json.loads(review_path.read_text(encoding="utf-8"))

        self.assertEqual(len(review_items), 1)
        self.assertEqual(saved_items, review_items)
        self.assertTrue(review_items[0]["manual_review_required"])
        self.assertIn("price", review_items[0]["missing_fields"])
        self.assertIn("dimensions", review_items[0]["missing_fields"])
        self.assertIn("material", review_items[0]["missing_fields"])
        self.assertIn("installation_service", review_items[0]["missing_fields"])
        self.assertIn("source", review_items[0]["missing_fields"])
        self.assertIn("确认价格", review_items[0]["suggested_action"])

    def test_review_does_not_flag_complete_product_without_reason(self) -> None:
        review_path = self.workspace / "manual_review_complete_items.json"
        products = [
            {
                "title": "完整办公屏风 1600x750x750",
                "url": "https://example.com/complete",
                "source": "客户公开资料",
                "price": 999,
                "material": "钢制框架，颗粒板",
                "dimensions": "1600x750x750mm",
                "specs_text": "尺寸：1600x750x750mm；材质：钢制框架，颗粒板。",
                "service_text": "支持配送和现场安装。",
                "evidence_text": "客户公开资料页面显示尺寸、材质、价格和现场安装服务。",
            }
        ]

        review_items = generate_manual_review_items(products, review_path)

        self.assertEqual(review_items, [])

    def test_main_pipeline_keeps_end_to_end_word_output_with_optional_review_path(self) -> None:
        output_dir = self.workspace / "main_pipeline"
        output_dir.mkdir(parents=True, exist_ok=True)
        review_path = output_dir / "manual_review_items.json"
        review_path.write_text("[]", encoding="utf-8")

        result = run_pipeline(products_json_path=self.root / "data" / "sample_products.json", output_dir=output_dir)

        self.assertTrue(Path(result["output_docx_path"]).exists())
        self.assertEqual(result["manual_review_path"], str(review_path))
        self.assertEqual(result["top_products_count"], 3)
        for field in [
            "requirements_count",
            "products_count",
            "ranked_products_count",
            "top_products_count",
            "responses_count",
            "requirements_path",
            "ranked_products_path",
            "responses_path",
            "output_docx_path",
            "products_source_path",
        ]:
            self.assertIn(field, result)


if __name__ == "__main__":
    unittest.main()
