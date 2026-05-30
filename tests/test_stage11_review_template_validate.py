import json
import unittest
from pathlib import Path

from src.crawler.review_template import TEMPLATE_FIELDS, generate_review_template
from src.crawler.review_validate import NOTICE, validate_review_filled


class Stage11ReviewTemplateValidateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(__file__).resolve().parents[1]
        self.workspace = self.root / "outputs" / "stage11_test_workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.case_index = 0

    def _write_json(self, name: str, data: object) -> Path:
        path = self.workspace / name
        path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return path

    def _validate(
        self,
        review_items: object,
        products: object | None = None,
    ) -> dict[str, object]:
        self.case_index += 1
        products = products if products is not None else [{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料"}]
        products_path = self._write_json(f"products_{self.case_index}.json", products)
        review_path = self._write_json(f"manual_review_filled_{self.case_index}.json", {"review_items": review_items})
        report_path = self.workspace / f"manual_review_validation_report_{self.case_index}.json"

        report = validate_review_filled(review_path, products_path, report_path)
        saved_report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report, saved_report)
        self.assertIn("不代表最终采购结论", report["notice"])
        self.assertEqual(report["notice"], NOTICE)
        return report

    def test_generates_fillable_template_from_manual_review_items(self) -> None:
        review_items_path = self._write_json(
            "manual_review_items.json",
            [
                {
                    "title": "原始标题",
                    "url": "https://example.com/original",
                    "source": "客户公开资料",
                    "missing_fields": ["price", "material"],
                    "risk_reason": "缺少可核验价格。",
                    "suggested_action": "请人工确认价格。",
                    "confirmed_price": 999,
                    "evidence_text": "旧清单中的证据文本不应自动回填到确认字段。",
                }
            ],
        )
        template_path = self.workspace / "manual_review_filled_template.json"

        template = generate_review_template(review_items_path, template_path)
        saved_template = json.loads(template_path.read_text(encoding="utf-8"))

        self.assertEqual(template, saved_template)
        self.assertEqual(len(template["review_items"]), 1)
        item = template["review_items"][0]
        self.assertEqual(set(TEMPLATE_FIELDS), set(item))
        self.assertEqual(item["title"], "原始标题")
        self.assertEqual(item["url"], "https://example.com/original")
        self.assertEqual(item["source"], "客户公开资料")
        self.assertEqual(item["missing_fields"], ["price", "material"])
        self.assertEqual(item["review_status"], "")
        self.assertEqual(item["review_note"], "")
        self.assertEqual(item["confirmed_price"], "")
        self.assertEqual(item["confirmed_source"], "")
        self.assertEqual(item["confirmed_fields"], [])

    def test_approved_without_confirmed_fields_warns(self) -> None:
        report = self._validate([{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "approved"}])

        self.assertEqual(report["error_count"], 0)
        self.assertTrue(any(item["code"] == "approved_without_confirmed_fields" for item in report["warnings"]))

    def test_invalid_review_status_errors(self) -> None:
        report = self._validate([{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "done"}])

        self.assertEqual(report["error_count"], 1)
        self.assertTrue(any(item["code"] == "invalid_review_status" for item in report["errors"]))
        self.assertEqual(report["valid_items_count"], 0)

    def test_rejected_without_review_note_warns(self) -> None:
        report = self._validate([{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "rejected"}])

        self.assertEqual(report["error_count"], 0)
        self.assertTrue(any(item["code"] == "rejected_without_note" for item in report["warnings"]))

    def test_needs_more_info_without_review_note_warns(self) -> None:
        report = self._validate(
            [{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "needs_more_info"}]
        )

        self.assertEqual(report["error_count"], 0)
        self.assertTrue(any(item["code"] == "needs_more_info_without_note" for item in report["warnings"]))

    def test_duplicate_url_is_reported(self) -> None:
        report = self._validate(
            [
                {"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "approved", "confirmed_price": 1},
                {"title": "匹配商品副本", "url": "https://example.com/a/", "source": "客户资料", "review_status": "approved", "confirmed_price": 2},
            ]
        )

        self.assertEqual(len(report["duplicate_items"]), 1)
        self.assertEqual(report["duplicate_items"][0]["match_key_type"], "url")

    def test_duplicate_title_source_is_reported_when_url_is_empty(self) -> None:
        report = self._validate(
            [
                {"title": "无链接商品", "url": "", "source": "客户 CSV", "review_status": "approved", "confirmed_price": 1},
                {"title": "无链接商品", "url": "", "source": "客户 CSV", "review_status": "approved", "confirmed_price": 2},
            ],
            products=[{"title": "无链接商品", "url": "", "source": "客户 CSV"}],
        )

        self.assertEqual(len(report["duplicate_items"]), 1)
        self.assertEqual(report["duplicate_items"][0]["match_key_type"], "title_source")

    def test_unknown_fields_are_reported_without_crash(self) -> None:
        report = self._validate(
            [
                {
                    "title": "匹配商品",
                    "url": "https://example.com/a",
                    "source": "客户资料",
                    "review_status": "approved",
                    "confirmed_price": 1,
                    "客户额外列": "仅用于测试",
                }
            ]
        )

        self.assertEqual(report["error_count"], 0)
        self.assertEqual(len(report["unknown_field_items"]), 1)
        self.assertIn("客户额外列", report["unknown_field_items"][0]["unknown_fields"])

    def test_unmatched_items_are_reported(self) -> None:
        report = self._validate(
            [{"title": "无法匹配商品", "url": "https://example.com/missing", "source": "客户资料", "review_status": "approved", "confirmed_price": 1}]
        )

        self.assertEqual(len(report["unmatched_items"]), 1)
        self.assertEqual(report["unmatched_items"][0]["title"], "无法匹配商品")

    def test_empty_review_status_enters_incomplete_items(self) -> None:
        report = self._validate([{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": ""}])

        self.assertEqual(report["error_count"], 0)
        self.assertEqual(len(report["incomplete_items"]), 1)
        self.assertEqual(report["incomplete_items"][0]["title"], "匹配商品")

    def test_confirmed_fields_must_be_array_or_parseable_string(self) -> None:
        valid_report = self._validate(
            [{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "approved", "confirmed_fields": "price,material"}]
        )
        invalid_report = self._validate(
            [{"title": "匹配商品", "url": "https://example.com/a", "source": "客户资料", "review_status": "approved", "confirmed_fields": {"price": True}}]
        )

        self.assertEqual(valid_report["error_count"], 0)
        self.assertEqual(invalid_report["error_count"], 1)
        self.assertTrue(any(item["code"] == "invalid_confirmed_fields" for item in invalid_report["errors"]))


if __name__ == "__main__":
    unittest.main()
