import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "export_api_inventory.py"


class ExportApiInventoryScriptContractTests(unittest.TestCase):
    def test_script_supports_emit_timings_flag(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("--emit-timings", text)
        self.assertIn("load_dependencies=", text)
        self.assertIn("build_payload=", text)

    def test_script_uses_lazy_runtime_dependency_loading(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("def _load_runtime_dependencies()", text)
        self.assertNotIn("from app.main import app as fastapi_app  # noqa: E402", text)
        self.assertNotIn("from app.api.deps import get_current_user  # noqa: E402", text)


if __name__ == "__main__":
    unittest.main()
