import ast
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
AI_PATH = BACKEND_ROOT / "app" / "services" / "ai.py"
LOGIN_PATH = BACKEND_ROOT / "app" / "api" / "login.py"
SECURITY_PATH = BACKEND_ROOT / "app" / "core" / "security.py"


class LazyImportContractTests(unittest.TestCase):
    @staticmethod
    def _top_level_import_from_names(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
        return imported

    def test_ai_module_does_not_import_openai_at_top_level(self) -> None:
        text = AI_PATH.read_text(encoding="utf-8")
        imported = self._top_level_import_from_names(AI_PATH)
        self.assertNotIn("openai", imported)
        self.assertIn("def _bootstrap_openai_support()", text)
        self.assertIn("def _get_openai_client()", text)

    def test_login_module_does_not_import_jose_at_top_level(self) -> None:
        text = LOGIN_PATH.read_text(encoding="utf-8")
        imported = self._top_level_import_from_names(LOGIN_PATH)
        self.assertNotIn("jose", imported)
        self.assertIn("def _get_jwt_backend()", text)
        self.assertIn("def _jwt_error_types()", text)

    def test_security_module_does_not_import_jose_at_top_level(self) -> None:
        text = SECURITY_PATH.read_text(encoding="utf-8")
        imported = self._top_level_import_from_names(SECURITY_PATH)
        self.assertNotIn("jose", imported)
        self.assertIn("def _get_jwt_backend()", text)


if __name__ == "__main__":
    unittest.main()
