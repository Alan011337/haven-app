import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = REPO_ROOT / "scripts" / "synthetics" / "run_cuj_synthetics.py"
_SPEC = importlib.util.spec_from_file_location("run_cuj_synthetics", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

evaluate_cuj_synthetic = _MODULE.evaluate_cuj_synthetic
classify_synthetic_failure = _MODULE.classify_synthetic_failure
main = _MODULE.main


class CujSyntheticsTests(unittest.TestCase):
    def test_evaluate_passes_on_ok_payload(self) -> None:
        stages, passed = evaluate_cuj_synthetic(
            health_payload={
                "status": "ok",
                "sli": {"http_runtime": {"sample_count": 100, "latency_ms": {"p95": 1200}}},
            },
            slo_payload={
                "sli": {
                    "evaluation": {
                        "ws": {"status": "ok"},
                        "ws_burn_rate": {"status": "ok"},
                        "cuj": {"status": "ok"},
                    }
                }
            },
        )
        self.assertTrue(passed)
        self.assertEqual(stages[0]["status"], "pass")
        self.assertEqual(classify_synthetic_failure(stages), "none")

    def test_evaluate_fails_when_ws_gate_degraded(self) -> None:
        stages, passed = evaluate_cuj_synthetic(
            health_payload={"status": "ok", "http_observability": {"sample_count": 1, "latency_ms": {"p95": 100}}},
            slo_payload={
                "sli": {
                    "evaluation": {
                        "ws": {"status": "degraded"},
                        "ws_burn_rate": {"status": "degraded"},
                        "cuj": {"status": "ok"},
                    }
                }
            },
        )
        self.assertFalse(passed)
        ws_stage = [item for item in stages if item["stage"] == "ws_slo_gate"][0]
        self.assertEqual(ws_stage["status"], "fail")
        self.assertEqual(classify_synthetic_failure(stages), "ws_slo_degraded")

    def test_evaluate_fails_when_cuj_gate_degraded(self) -> None:
        stages, passed = evaluate_cuj_synthetic(
            health_payload={"status": "ok", "sli": {"http_runtime": {"sample_count": 1, "latency_ms": {"p95": 100}}}},
            slo_payload={
                "sli": {
                    "evaluation": {
                        "ws": {"status": "ok"},
                        "ws_burn_rate": {"status": "ok"},
                        "cuj": {"status": "degraded"},
                    }
                }
            },
        )
        self.assertFalse(passed)
        cuj_stage = [item for item in stages if item["stage"] == "cuj_slo_gate"][0]
        self.assertEqual(cuj_stage["status"], "fail")
        self.assertEqual(classify_synthetic_failure(stages), "cuj_slo_degraded")

    def test_main_allows_missing_url(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            exit_code = main(["--allow-missing-url"])
        self.assertEqual(exit_code, 0)

    def test_main_writes_evidence(self) -> None:
        health_payload = {
            "status": "ok",
            "http_observability": {
                "sample_count": 10,
                "latency_ms": {"p95": 1000},
            },
        }
        slo_payload = {
            "sli": {
                "evaluation": {
                    "ws": {"status": "ok"},
                    "ws_burn_rate": {"status": "ok"},
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.object(_MODULE, "_fetch_json", side_effect=[health_payload, slo_payload]):
                exit_code = main([
                    "--base-url",
                    "https://example.com",
                    "--output-dir",
                    tmp_dir,
                    "--summary-path",
                    str(Path(tmp_dir) / "summary.json"),
                ])

            files = list(Path(tmp_dir).glob("cuj-synthetic-*.json"))
            summary_payload = json.loads((Path(tmp_dir) / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(exit_code, 0)
            self.assertTrue(files)
            self.assertEqual(summary_payload["result"], "pass")
            self.assertEqual(summary_payload["failure_class"], "none")
            self.assertEqual(summary_payload["failed_stages"], [])

    def test_main_supports_offline_payload_files(self) -> None:
        health_payload = {
            "status": "ok",
            "sli": {"http_runtime": {"sample_count": 10, "latency_ms": {"p95": 800}}},
        }
        slo_payload = {
            "sli": {
                "evaluation": {
                    "ws": {"status": "ok"},
                    "ws_burn_rate": {"status": "ok"},
                    "cuj": {"status": "insufficient_data"},
                }
            }
        }
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            health_path = tmp_path / "health.json"
            slo_path = tmp_path / "slo.json"
            summary_path = tmp_path / "summary.json"
            health_path.write_text(json.dumps(health_payload), encoding="utf-8")
            slo_path.write_text(json.dumps(slo_payload), encoding="utf-8")

            exit_code = main(
                [
                    "--health-payload-file",
                    str(health_path),
                    "--slo-payload-file",
                    str(slo_path),
                    "--output-dir",
                    tmp_dir,
                    "--summary-path",
                    str(summary_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            evidence_files = list(tmp_path.glob("cuj-synthetic-*.json"))
            self.assertTrue(evidence_files)
            summary_payload = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary_payload["result"], "pass")
            self.assertEqual(summary_payload["failure_class"], "none")


if __name__ == "__main__":
    unittest.main()
