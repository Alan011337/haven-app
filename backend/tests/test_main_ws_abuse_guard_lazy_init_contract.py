import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
MAIN_PATH = BACKEND_ROOT / "app" / "main.py"


class MainWsAbuseGuardLazyInitContractTests(unittest.TestCase):
    def test_ws_abuse_guard_is_lazily_initialized(self) -> None:
        text = MAIN_PATH.read_text(encoding="utf-8")
        self.assertIn("_ws_abuse_guard: WsAbuseGuard | None = None", text)
        self.assertIn("def _get_ws_abuse_guard()", text)
        self.assertIn("ws_abuse_guard = _get_ws_abuse_guard()", text)
        self.assertNotIn("\nws_abuse_guard = WsAbuseGuard(", text)


if __name__ == "__main__":
    unittest.main()
