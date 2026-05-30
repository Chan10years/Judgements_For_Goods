import json
import unittest
from pathlib import Path
from unittest.mock import patch

from main import _select_products_json_path, run_pipeline
from src.crawler.deduper import dedupe_products
from src.crawler.models import CrawlerConfig, FetchResult, RobotsDecision, SeedUrl
from src.crawler.parser import parse_product_page
from src.crawler.pipeline import run_crawler
from src.crawler.seed_loader import load_seed_urls


class Stage8CrawlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        (self.root / "outputs").mkdir(parents=True, exist_ok=True)
        self.test_workspace = self.root / "outputs" / "stage8_test_workspace"
        self.test_workspace.mkdir(parents=True, exist_ok=True)

    def _valid_config_data(self) -> dict[str, object]:
        return {
            "user_agent": "Stage81TestCrawler/1.0",
            "timeout_seconds": 10,
            "max_retries": 0,
            "retry_backoff_seconds": 0,
            "request_interval_seconds": 2,
            "respect_robots_txt": True,
            "max_urls_per_run": 20,
            "output_raw_path": "outputs/stage8_test_workspace/raw.json",
            "output_products_path": "outputs/stage8_test_workspace/products.json",
            "output_report_path": "outputs/stage8_test_workspace/report.json",
            "log_path": "outputs/stage8_test_workspace/crawler.log",
        }

    def test_crawler_config_rejects_non_conservative_values(self) -> None:
        invalid_cases = [
            ("timeout_seconds", 9),
            ("request_interval_seconds", 1),
            ("max_urls_per_run", 21),
            ("respect_robots_txt", False),
            ("max_retries", -1),
            ("retry_backoff_seconds", -1),
            ("user_agent", ""),
            ("output_products_path", ""),
        ]

        for field, value in invalid_cases:
            with self.subTest(field=field):
                config_data = self._valid_config_data()
                config_data[field] = value
                with self.assertRaises(ValueError):
                    CrawlerConfig.from_dict(config_data)

    def test_seed_loader_validates_and_dedupes_urls(self) -> None:
        seed_path = self.test_workspace / "seed_urls_test.json"
        seed_path.write_text(
            json.dumps(
                [
                    {
                        "url": "https://example.com/product-a",
                        "source_name": "Example",
                        "category_hint": "办公家具",
                        "note": "公开测试 URL",
                    },
                    {
                        "url": "https://example.com/product-a#section",
                        "source_name": "Example",
                        "category_hint": "办公家具",
                        "note": "重复 URL",
                    },
                    {
                        "url": "local://invalid",
                        "source_name": "Invalid",
                        "category_hint": "",
                        "note": "非法协议",
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        seeds, invalid_entries = load_seed_urls(seed_path)

        self.assertEqual(len(seeds), 1)
        self.assertEqual(seeds[0].url, "https://example.com/product-a")
        self.assertEqual(len(invalid_entries), 2)

    def test_parser_extracts_product_fields_without_inventing_missing_values(self) -> None:
        html = """
        <html>
          <head>
            <title>办公屏风工位隔断桌</title>
            <meta name="description" content="工程采购办公屏风样例">
          </head>
          <body>
            <h1>办公屏风工位隔断桌 1600x750x750</h1>
            <p>价格：899</p>
            <table>
              <tr><th>尺寸</th><td>1600x750x750mm</td></tr>
              <tr><th>材质</th><td>钢制框架，实木颗粒板</td></tr>
            </table>
            <p>支持配送，支持现场安装，提供售后咨询。</p>
          </body>
        </html>
        """
        seed = SeedUrl(
            url="https://example.com/product-a",
            source_name="Example",
            category_hint="办公家具",
            note="公开测试 URL",
        )

        parsed = parse_product_page(html, seed)

        self.assertIn("办公屏风", parsed["title"])
        self.assertEqual(parsed["price"], "899")
        self.assertIn("尺寸", parsed["specs_text"])
        self.assertIn("安装", parsed["service_text"])
        self.assertEqual(parsed["material"], "")
        self.assertEqual(parsed["color"], "")
        self.assertEqual(parsed["dimensions"], "")
        self.assertLessEqual(len(parsed["raw_text"]), 2000)
        self.assertTrue(parsed["evidence_text"])

    def test_parser_rejects_page_without_title_even_with_body_text(self) -> None:
        html = """
        <html><body>
          <p>这是一段普通正文，包含办公家具、价格：899、配送安装等文字。</p>
        </body></html>
        """
        seed = SeedUrl(
            url="https://example.com/no-title",
            source_name="Example",
            category_hint="办公家具",
            note="公开测试 URL",
        )

        parsed = parse_product_page(html, seed)

        self.assertFalse(parsed["parse_success"])
        self.assertIn("标题", parsed["parse_error"])
        self.assertIn("title", parsed["missing_fields"])
        self.assertTrue(parsed["raw_text"])

    def test_parser_does_not_invent_missing_product_attributes(self) -> None:
        html = """
        <html>
          <head><title>办公屏风候选商品</title></head>
          <body><h1>办公屏风候选商品</h1><p>仅有商品标题，没有价格和服务承诺。</p></body>
        </html>
        """
        seed = SeedUrl(
            url="https://example.com/missing-fields",
            source_name="Example",
            category_hint="办公家具",
            note="公开测试 URL",
        )

        parsed = parse_product_page(html, seed)

        self.assertTrue(parsed["parse_success"])
        self.assertEqual(parsed["price"], "")
        self.assertEqual(parsed["material"], "")
        self.assertEqual(parsed["color"], "")
        self.assertEqual(parsed["dimensions"], "")
        self.assertEqual(parsed["service_text"], "")
        self.assertIn("price", parsed["missing_fields"])
        self.assertIn("service_text", parsed["missing_fields"])
        self.assertTrue(parsed["manual_review_required"])

    def test_deduper_prefers_url_and_weak_key_without_url(self) -> None:
        products = [
            {"title": "A", "price": 100, "dimensions": "1600x750x750", "url": "https://example.com/a"},
            {"title": "A copy", "price": 200, "dimensions": "1400x700x750", "url": "https://example.com/a/"},
            {"title": "B", "price": 300, "dimensions": "1600x750x750", "url": ""},
            {"title": "B", "price": 300, "dimensions": "1600x750x750", "url": ""},
        ]

        deduped, report = dedupe_products(products)

        self.assertEqual(len(deduped), 2)
        self.assertEqual(report["before_count"], 4)
        self.assertEqual(report["after_count"], 2)
        reasons = [item["reason"] for item in report["duplicates"]]
        self.assertIn("duplicate_url", reasons)
        self.assertIn("duplicate_title_price_specs", reasons)

    def test_deduper_uses_specs_summary_when_url_and_dimensions_are_empty(self) -> None:
        products = [
            {
                "title": "办公屏风工位隔断桌",
                "price": 899,
                "dimensions": "",
                "specs_text": "尺寸：1600x750x750mm；材质：钢制框架；颜色：灰白色；支持配送安装。",
                "url": "",
            },
            {
                "title": "办公屏风工位隔断桌",
                "price": "899",
                "dimensions": "",
                "specs_text": "尺寸：1600x750x750mm；材质：钢制框架；颜色：灰白色；支持配送安装。",
                "url": "",
            },
        ]

        deduped, report = dedupe_products(products)

        self.assertEqual(len(deduped), 1)
        self.assertEqual(report["removed_count"], 1)
        self.assertEqual(report["duplicates"][0]["reason"], "duplicate_title_price_specs")

    def test_run_crawler_writes_outputs_with_mocked_fetcher(self) -> None:
        html = """
        <html><body>
          <h1>办公屏风工位隔断桌 1600x750x750</h1>
          <p>价格：899</p>
          <p>规格参数：钢制框架，实木颗粒板，灰白色。</p>
          <p>服务：支持配送和现场安装。</p>
        </body></html>
        """
        temp_root = self.test_workspace / "pipeline"
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
                    "user_agent": "Stage8TestCrawler/1.0",
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
                        "url": "https://example.com/product-a",
                        "source_name": "Example",
                        "category_hint": "办公家具",
                        "note": "公开测试 URL",
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
                text=html,
                error_type="",
                error_message="",
                attempts=1,
                elapsed_seconds=0.01,
            )

        with patch("src.crawler.robots_checker.RobotsChecker.can_fetch", fake_can_fetch), patch(
            "src.crawler.fetcher.ProductFetcher.fetch", fake_fetch
        ):
            report = run_crawler(config_path=config_path, seed_path=seed_path)

        products = json.loads(products_path.read_text(encoding="utf-8"))

        self.assertEqual(report["total_url_count"], 1)
        self.assertEqual(report["valid_url_count"], 1)
        self.assertEqual(report["success_count"], 1)
        self.assertEqual(report["dedupe_after_count"], 1)
        self.assertTrue(raw_path.exists())
        self.assertTrue(report_path.exists())
        self.assertTrue(log_path.exists())
        self.assertEqual(products[0]["source"], "Example")

    def test_main_pipeline_falls_back_when_crawler_products_empty(self) -> None:
        result = run_pipeline(products_json_path=None)

        self.assertGreaterEqual(result["products_count"], 1)
        self.assertTrue(Path(result["products_source_path"]).name in {"crawler_products.json", "sample_products.json"})

    def test_main_selects_fallback_when_crawler_products_are_invalid(self) -> None:
        invalid_path = self.test_workspace / "invalid_crawler_products.json"
        fallback_path = self.root / "data" / "sample_products.json"
        invalid_cases = [
            "",
            "{bad json",
            "[]",
            json.dumps([{"title": "缺少来源"}], ensure_ascii=False),
            json.dumps([{"url": "https://example.com/no-title"}], ensure_ascii=False),
            json.dumps({"products": [{"title": "缺少来源"}]}, ensure_ascii=False),
        ]

        for index, content in enumerate(invalid_cases, start=1):
            with self.subTest(index=index):
                invalid_path.write_text(content, encoding="utf-8")
                selected = _select_products_json_path(invalid_path, fallback_path)
                self.assertEqual(selected, fallback_path)


if __name__ == "__main__":
    unittest.main()
