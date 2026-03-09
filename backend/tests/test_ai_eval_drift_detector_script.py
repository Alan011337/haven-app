import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_ai_eval_drift_detector.py"
_SPEC = importlib.util.spec_from_file_location("run_ai_eval_drift_detector", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _base_snapshot(*, drift_score: float) -> dict[str, object]:
    return {
        "artifact_kind": "ai-quality-snapshot",
        "schema_version": "1.0.0",
        "generated_at": "2026-02-23T00:00:00Z",
        "thresholds": {
            "drift_score_max": 0.2,
        },
        "evaluation": {
            "result": "pass",
            "drift_score": drift_score,
            "degraded_reasons": [],
        },
    }


def _base_policy(*, drift_score_max: float = 0.2) -> dict[str, object]:
    return {
        "artifact_kind": "ai-cost-quality-policy",
        "schema_version": "1.0.0",
        "thresholds": {
            "drift_score_max": drift_score_max,
        },
    }


class AIEvalDriftDetectorScriptTests(unittest.TestCase):
    def test_main_writes_pass_result_when_drift_within_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "snapshot.json"
            policy_path = Path(tmp_dir) / "policy.json"
            output_path = Path(tmp_dir) / "drift.json"
            latest_path = Path(tmp_dir) / "drift-latest.json"
            summary_path = Path(tmp_dir) / "drift-summary.json"

            snapshot_path.write_text(
                json.dumps(_base_snapshot(drift_score=0.12)),
                encoding="utf-8",
            )
            policy_path.write_text(
                json.dumps(_base_policy(drift_score_max=0.2)),
                encoding="utf-8",
            )

            exit_code = _MODULE.main(
                [
                    "--snapshot",
                    str(snapshot_path),
                    "--policy",
                    str(policy_path),
                    "--output",
                    str(output_path),
                    "--latest-path",
                    str(latest_path),
                    "--summary-path",
                    str(summary_path),
                ]
            )
            self.assertEqual(exit_code, 0)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_kind"], "ai-eval-drift-detector")
            self.assertEqual(payload["evaluation"]["result"], "pass")
            self.assertFalse(payload["evaluation"]["alert_open"])
            self.assertEqual(payload["evaluation"]["reasons"], [])
            self.assertTrue(latest_path.exists())
            self.assertTrue(summary_path.exists())

    def test_main_marks_degraded_when_drift_exceeds_max(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "snapshot.json"
            policy_path = Path(tmp_dir) / "policy.json"
            output_path = Path(tmp_dir) / "drift.json"
            summary_path = Path(tmp_dir) / "drift-summary.json"

            snapshot_path.write_text(
                json.dumps(_base_snapshot(drift_score=0.24)),
                encoding="utf-8",
            )
            policy_path.write_text(
                json.dumps(_base_policy(drift_score_max=0.2)),
                encoding="utf-8",
            )

            exit_code = _MODULE.main(
                [
                    "--snapshot",
                    str(snapshot_path),
                    "--policy",
                    str(policy_path),
                    "--output",
                    str(output_path),
                    "--summary-path",
                    str(summary_path),
                ]
            )
            self.assertEqual(exit_code, 0)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["evaluation"]["result"], "degraded")
            self.assertTrue(payload["evaluation"]["alert_open"])
            self.assertIn("drift_score_above_max", payload["evaluation"]["reasons"])

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "degraded")

    def test_main_marks_critical_and_fail_on_alert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "snapshot.json"
            policy_path = Path(tmp_dir) / "policy.json"
            output_path = Path(tmp_dir) / "drift.json"

            snapshot_path.write_text(
                json.dumps(_base_snapshot(drift_score=0.35)),
                encoding="utf-8",
            )
            policy_path.write_text(
                json.dumps(_base_policy(drift_score_max=0.2)),
                encoding="utf-8",
            )

            exit_code = _MODULE.main(
                [
                    "--snapshot",
                    str(snapshot_path),
                    "--policy",
                    str(policy_path),
                    "--output",
                    str(output_path),
                    "--critical-multiplier",
                    "1.5",
                    "--fail-on-alert",
                ]
            )
            self.assertEqual(exit_code, 1)

            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["evaluation"]["result"], "critical")
            self.assertIn("drift_score_above_critical", payload["evaluation"]["reasons"])


if __name__ == "__main__":
    unittest.main()
