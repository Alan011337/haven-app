import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_error_budget_freeze_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_error_budget_freeze_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

evaluate_release_freeze = _MODULE.evaluate_release_freeze
main = _MODULE.main


class ErrorBudgetFreezeGateTests(unittest.TestCase):
    def test_evaluate_passes_when_freeze_disabled(self) -> None:
        passed, reasons, meta = evaluate_release_freeze(
            {"release_freeze": False, "checked_at": "2026-02-22T00:00:00Z"},
            hotfix_override=False,
        )
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertFalse(meta["release_freeze"])

    def test_evaluate_fails_when_freeze_enabled_without_override(self) -> None:
        passed, reasons, meta = evaluate_release_freeze(
            {"release_freeze": True, "reason": "SLO-01 breach"},
            hotfix_override=False,
        )
        self.assertFalse(passed)
        self.assertIn("release_freeze_active", reasons)
        self.assertFalse(meta["override"])

    def test_evaluate_passes_with_hotfix_override(self) -> None:
        passed, reasons, meta = evaluate_release_freeze(
            {"release_freeze": True, "reason": "SLO-02 breach"},
            hotfix_override=True,
        )
        self.assertTrue(passed)
        self.assertIn("release_freeze_active", reasons)
        self.assertIn("hotfix_override_enabled", reasons)
        self.assertTrue(meta["override"])

    def test_main_allows_missing_status_with_flag(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            exit_code = main(["--allow-missing-status", "--status-file", "/tmp/does-not-exist.json"])
        self.assertEqual(exit_code, 0)

    def test_main_fails_when_status_file_indicates_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_path = Path(tmp_dir) / "status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "release_freeze": True,
                        "checked_at": "2026-02-22T00:00:00Z",
                        "reason": "SLO-01 below objective",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                exit_code = main(["--status-file", str(status_path)])
        self.assertEqual(exit_code, 1)

    def test_main_passes_when_hotfix_override_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            status_path = Path(tmp_dir) / "status.json"
            status_path.write_text(
                json.dumps(
                    {
                        "release_freeze": True,
                        "checked_at": "2026-02-22T00:00:00Z",
                        "reason": "SLO-02 below objective",
                    }
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"RELEASE_GATE_HOTFIX_OVERRIDE": "1"}, clear=True):
                exit_code = main(["--status-file", str(status_path)])
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
