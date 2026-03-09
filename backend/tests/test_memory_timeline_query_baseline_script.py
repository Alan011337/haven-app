from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "export_memory_timeline_query_baseline.py"
_SPEC = importlib.util.spec_from_file_location("export_memory_timeline_query_baseline", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load baseline script from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class MemoryTimelineQueryBaselineScriptTests(unittest.TestCase):
    def test_build_baseline_payload_contains_index_usage(self) -> None:
        payload = _MODULE.build_baseline_payload()
        plan = payload["timeline_query_plan"]
        self.assertTrue(plan["journal"]["index_detected"])
        self.assertTrue(plan["card_session"]["index_detected"])
        self.assertFalse(plan["journal"]["uses_date_function"])
        self.assertFalse(plan["card_session"]["uses_date_function"])
        self.assertFalse(plan["journal"]["full_scan_detected"])
        self.assertFalse(plan["card_session"]["full_scan_detected"])
        self.assertGreater(len(plan["journal"]["plan_details"]), 0)
        self.assertGreater(len(plan["card_session"]["plan_details"]), 0)

    def test_script_writes_output_and_supports_fail_on_missing_index(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "timeline-baseline.json"
            code = _MODULE.main(
                [
                    "--output",
                    str(output_path),
                    "--fail-on-missing-index",
                    "--fail-on-date-function",
                    "--fail-on-full-scan",
                ]
            )
            self.assertEqual(code, 0)
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertIn("timeline_query_plan", payload)


if __name__ == "__main__":
    unittest.main()
