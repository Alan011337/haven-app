import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_pricing_experiment_guardrail_snapshot.py"
_SPEC = importlib.util.spec_from_file_location("run_pricing_experiment_guardrail_snapshot", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class PricingExperimentGuardrailSnapshotScriptTests(unittest.TestCase):
    def test_script_allows_missing_metrics_when_flag_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "guardrail.json"
            latest_path = Path(tmpdir) / "guardrail-latest.json"
            exit_code = _MODULE.main(
                [
                    "--allow-missing-metrics",
                    "--output",
                    str(output_path),
                    "--latest-path",
                    str(latest_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["artifact_kind"], "pricing-experiment-guardrail-snapshot")
            self.assertEqual(payload["evaluation"]["status"], "insufficient_data")

    def test_script_fails_on_triggered_when_fail_mode_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            metrics_path = Path(tmpdir) / "metrics.json"
            output_path = Path(tmpdir) / "guardrail.json"
            latest_path = Path(tmpdir) / "guardrail-latest.json"
            metrics_path.write_text(
                json.dumps(
                    {
                        "metrics": {
                            "pricing.experiment.refund_rate": 0.2,
                            "pricing.experiment.chargeback_rate": 0.001,
                            "pricing.experiment.p0_cuj_failure_rate": 0.0001,
                            "pricing.experiment.support_ticket_rate": 0.01,
                        }
                    }
                ),
                encoding="utf-8",
            )
            exit_code = _MODULE.main(
                [
                    "--metrics-path",
                    str(metrics_path),
                    "--output",
                    str(output_path),
                    "--latest-path",
                    str(latest_path),
                    "--fail-on-triggered",
                ]
            )

            self.assertEqual(exit_code, 1)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["evaluation"]["status"], "triggered")
            self.assertEqual(payload["evaluation"]["breaches"][0]["metric"], "pricing.experiment.refund_rate")


if __name__ == "__main__":
    unittest.main()
