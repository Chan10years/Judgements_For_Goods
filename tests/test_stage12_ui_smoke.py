import importlib
import inspect
import sys
import types
import unittest


class _StreamlitTrap(types.ModuleType):
    def __init__(self) -> None:
        super().__init__("streamlit")
        self.accessed: list[str] = []

    def __getattr__(self, name: str) -> object:
        self.accessed.append(name)
        raise AssertionError(f"streamlit.{name} should not be accessed during import")


class Stage12UISmokeTests(unittest.TestCase):
    def test_ui_streamlit_imports_without_running_streamlit_flow(self) -> None:
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

        self.assertTrue(callable(getattr(module, "render_app", None)) or callable(getattr(module, "main", None)))
        self.assertEqual(trap.accessed, [])

    def test_stage12_action_functions_exist(self) -> None:
        import ui_streamlit

        for name in [
            "run_crawler_action",
            "run_main_pipeline_action",
            "generate_review_template_action",
            "validate_review_filled_action",
            "apply_review_action",
        ]:
            self.assertTrue(callable(getattr(ui_streamlit, name, None)), name)

    def test_legacy_public_interfaces_are_still_present(self) -> None:
        from main import run_pipeline
        from src.doc_writer import write_responses
        from src.product_loader import load_products_json
        from src.product_ranker import rank_products
        from src.response_builder import build_recommendation_responses, select_top_products

        self.assertEqual(
            list(inspect.signature(write_responses).parameters)[:3],
            ["input_docx_path", "responses", "output_docx_path"],
        )
        self.assertIn("summary_products", inspect.signature(write_responses).parameters)
        self.assertEqual(list(inspect.signature(load_products_json).parameters), ["path"])
        self.assertEqual(list(inspect.signature(rank_products).parameters), ["products", "requirements"])
        self.assertEqual(
            list(inspect.signature(build_recommendation_responses).parameters),
            ["requirements", "ranked_products", "top_n"],
        )
        self.assertEqual(list(inspect.signature(select_top_products).parameters), ["ranked_products", "top_n"])
        self.assertIn("input_docx_path", inspect.signature(run_pipeline).parameters)
        self.assertIn("products_json_path", inspect.signature(run_pipeline).parameters)
        self.assertIn("output_dir", inspect.signature(run_pipeline).parameters)


if __name__ == "__main__":
    unittest.main()
