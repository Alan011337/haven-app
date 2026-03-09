import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_cuj_synthetic_evidence_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_cuj_synthetic_evidence_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

evaluate_cuj_synthetic_evidence = _MODULE.evaluate_cuj_synthetic_evidence
main = _MODULE.main


class CujSyntheticEvidenceGateTests(unittest.TestCase):
    def _valid_payload(self) -> dict:
        return {
            "generated_at": "2026-02-22T00:00:00+00:00",
            "base_url": "https://example.com",
            "result": "pass",
            "failure_class": "none",
            "failed_stages": [],
            "warn_stages": [],
            "strict_mode": False,
            "stages": [
                {"stage": "health_endpoint", "status": "pass", "detail": "ok"},
                {"stage": "ws_slo_gate", "status": "pass", "detail": "ws=ok"},
                {"stage": "cuj_slo_gate", "status": "pass", "detail": "cuj=ok"},
                {"stage": "cuj_01_ritual", "status": "pass", "detail": "proxy ok"},
                {"stage": "cuj_02_journal", "status": "pass", "detail": "p95=1000"},
            ],
        }

    def test_evaluate_passes_for_valid_fresh_payload(self) -> None:
        payload = self._valid_payload()
        passed, reasons, meta = evaluate_cuj_synthetic_evidence(
            payload,
            max_age_hours=48.0,
            require_pass=True,
            now_utc=datetime(2026, 2, 22, 6, 0, tzinfo=UTC),
        )
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertEqual(meta["result"], "pass")
        self.assertEqual(meta["failure_class"], "none")

    def test_evaluate_fails_when_evidence_stale(self) -> None:
        payload = self._valid_payload()
        passed, reasons, _meta = evaluate_cuj_synthetic_evidence(
            payload,
            max_age_hours=1.0,
            require_pass=False,
            now_utc=datetime(2026, 2, 22, 6, 0, tzinfo=UTC),
        )
        self.assertFalse(passed)
        self.assertIn("evidence_stale", reasons)

    def test_evaluate_fails_when_require_pass_and_result_fail(self) -> None:
        payload = self._valid_payload()
        payload["result"] = "fail"
        payload["failure_class"] = "ws_slo_degraded"
        payload["failed_stages"] = ["ws_slo_gate"]
        passed, reasons, _meta = evaluate_cuj_synthetic_evidence(
            payload,
            max_age_hours=48.0,
            require_pass=True,
            now_utc=datetime(2026, 2, 22, 1, 0, tzinfo=UTC),
        )
        self.assertFalse(passed)
        self.assertIn("result_not_pass", reasons)

    def test_main_allows_missing_evidence_when_flag_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            exit_code = main(
                [
                    "--evidence-dir",
                    tmp_dir,
                    "--allow-missing-evidence",
                ]
            )
        self.assertEqual(exit_code, 0)

    def test_main_writes_summary_for_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            evidence_dir = Path(tmp_dir) / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_file = evidence_dir / "cuj-synthetic-20260222T000000Z.json"
            payload = self._valid_payload()
            payload["generated_at"] = datetime.now(UTC).isoformat()
            evidence_file.write_text(json.dumps(payload), encoding="utf-8")
            summary_path = Path(tmp_dir) / "summary.json"

            exit_code = main(
                [
                    "--evidence-dir",
                    str(evidence_dir),
                    "--require-pass",
                    "--summary-path",
                    str(summary_path),
                ]
            )
            self.assertEqual(exit_code, 0)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "pass")
            self.assertEqual(summary["reasons"], [])

    def test_main_fails_for_invalid_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            evidence_dir = Path(tmp_dir) / "evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            evidence_file = evidence_dir / "cuj-synthetic-20260222T000000Z.json"
            payload = self._valid_payload()
            payload.pop("failure_class", None)
            evidence_file.write_text(json.dumps(payload), encoding="utf-8")

            exit_code = main(
                [
                    "--evidence-dir",
                    str(evidence_dir),
                ]
            )
            self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
