from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_perf_baseline.py"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_perf_baseline", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class PerfBaselineScriptTests(unittest.TestCase):
    def test_run_perf_baseline_outputs_v1_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "perf-baseline.json"
            rc = _MODULE.main(
                [
                    "--iterations",
                    "2",
                    "--auth-p95-budget-ms",
                    "5000",
                    "--journal-write-p95-budget-ms",
                    "5000",
                    "--card-write-p95-budget-ms",
                    "5000",
                    "--timeline-query-p95-budget-ms",
                    "5000",
                    "--output",
                    str(output_path),
                    "--fail-on-budget-breach",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload.get("schema_version"), "v1")
            self.assertIn("results", payload)
            self.assertIn("auth_verify", payload["results"])
            self.assertIn("journal_write", payload["results"])
            self.assertIn("card_write", payload["results"])
            self.assertIn("timeline_query", payload["results"])
            self.assertIn("evaluation", payload)
            self.assertIn("query_plan_samples", payload)
            self.assertIn("timeline_journals", payload["query_plan_samples"])
            self.assertIn("timeline_card_sessions", payload["query_plan_samples"])
            self.assertIn(payload.get("status"), {"pass", "fail"})


if __name__ == "__main__":
    unittest.main()
