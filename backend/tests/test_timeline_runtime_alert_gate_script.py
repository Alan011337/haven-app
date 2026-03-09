from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_timeline_runtime_alert_gate.py"


def _build_slo_payload(*, query_total: int, clamped_total: int) -> dict[str, object]:
    return {
        "sli": {
            "timeline_runtime": {
                "counters": {
                    "timeline_query_total": query_total,
                    "timeline_budget_clamped_total": clamped_total,
                }
            }
        }
    }


class TimelineRuntimeAlertGateScriptTests(unittest.TestCase):
    def test_pass_when_clamp_ratio_within_threshold(self) -> None:
        payload = _build_slo_payload(query_total=100, clamped_total=5)
        with tempfile.TemporaryDirectory() as td:
            slo_file = Path(td) / "health-slo.json"
            summary_file = Path(td) / "summary.json"
            slo_file.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--health-slo-file",
                    str(slo_file),
                    "--summary-path",
                    str(summary_file),
                ],
                cwd=str(BACKEND_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            summary = json.loads(summary_file.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "pass")
            self.assertAlmostEqual(summary["meta"]["clamp_ratio"], 0.05)

    def test_degraded_returns_nonzero_when_fail_on_alert(self) -> None:
        payload = _build_slo_payload(query_total=100, clamped_total=20)
        with tempfile.TemporaryDirectory() as td:
            slo_file = Path(td) / "health-slo.json"
            slo_file.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--health-slo-file",
                    str(slo_file),
                    "--fail-on-alert",
                ],
                cwd=str(BACKEND_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertNotEqual(proc.returncode, 0, msg=proc.stdout)
            self.assertIn("status: degraded", proc.stdout)

    def test_allow_missing_payload_skips(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            summary_file = Path(td) / "summary.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--allow-missing-payload",
                    "--summary-path",
                    str(summary_file),
                ],
                cwd=str(BACKEND_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            summary = json.loads(summary_file.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "skipped")
            self.assertIn("missing_payload", summary["reasons"])


if __name__ == "__main__":
    unittest.main()
