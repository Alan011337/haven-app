import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_ai_eval_golden_set_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_ai_eval_golden_set_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _policy_payload() -> dict[str, object]:
    return {
        "artifact_kind": "ai-eval-golden-set",
        "schema_version": "1.0.0",
        "version": "2026-02-23.v1",
        "total_cases": 120,
        "gate_thresholds": {
            "min_cases_per_run": 100,
            "min_exact_match_rate": 0.9,
            "max_safety_tier_mismatch_rate": 0.03,
            "max_schema_failure_rate": 0.01,
        },
    }


def _results_payload(*, exact_match: float = 0.93) -> dict[str, object]:
    return {
        "artifact_kind": "ai-eval-golden-set-results",
        "schema_version": "1.0.0",
        "version": "2026-02-23.v1",
        "generated_at": "2026-02-23T04:00:00Z",
        "evaluated_cases": 120,
        "exact_match_rate": exact_match,
        "safety_tier_mismatch_rate": 0.01,
        "schema_failure_rate": 0.004,
    }


class AIEvalGoldenSetSnapshotScriptTests(unittest.TestCase):
    def test_main_writes_pass_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            results_path = Path(tmp_dir) / "results.json"
            output_path = Path(tmp_dir) / "snapshot.json"
            summary_path = Path(tmp_dir) / "summary.json"

            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")
            results_path.write_text(json.dumps(_results_payload()), encoding="utf-8")

            exit_code = _MODULE.main(
                [
                    "--policy",
                    str(policy_path),
                    "--results",
                    str(results_path),
                    "--output",
                    str(output_path),
                    "--summary-path",
                    str(summary_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_kind"], "ai-eval-golden-set-snapshot")
            self.assertEqual(payload["evaluation"]["status"], "pass")
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "pass")

    def test_main_reports_degraded_when_threshold_breached(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            results_path = Path(tmp_dir) / "results.json"
            output_path = Path(tmp_dir) / "snapshot.json"

            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")
            results = _results_payload(exact_match=0.85)
            results_path.write_text(json.dumps(results), encoding="utf-8")

            exit_code = _MODULE.main(
                [
                    "--policy",
                    str(policy_path),
                    "--results",
                    str(results_path),
                    "--output",
                    str(output_path),
                    "--fail-on-degraded",
                ]
            )
            self.assertEqual(exit_code, 1)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["evaluation"]["status"], "degraded")
            self.assertIn("exact_match_rate_below_min", payload["evaluation"]["reasons"])

    def test_main_allows_missing_results_with_insufficient_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            policy_path = Path(tmp_dir) / "policy.json"
            output_path = Path(tmp_dir) / "snapshot.json"

            policy_path.write_text(json.dumps(_policy_payload()), encoding="utf-8")

            exit_code = _MODULE.main(
                [
                    "--policy",
                    str(policy_path),
                    "--results",
                    str(Path(tmp_dir) / "missing-results.json"),
                    "--allow-missing-results",
                    "--output",
                    str(output_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["evaluation"]["status"], "insufficient_data")
            self.assertIn("missing_results_file", payload["evaluation"]["reasons"])


if __name__ == "__main__":
    unittest.main()
