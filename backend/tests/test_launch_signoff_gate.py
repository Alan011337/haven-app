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

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_launch_signoff_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_launch_signoff_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

evaluate_launch_signoff_artifact = _MODULE.evaluate_launch_signoff_artifact
main = _MODULE.main


class LaunchSignoffGateTests(unittest.TestCase):
    def _valid_payload(self) -> dict:
        return {
            "generated_at_utc": "20260222T000000Z",
            "overall_ready": False,
            "checks": [
                {
                    "id": "release_checklist_complete",
                    "status": "fail",
                    "detail": "release checklist has open items",
                },
                {
                    "id": "launch_gate_complete",
                    "status": "fail",
                    "detail": "launch gate has open items",
                },
                {
                    "id": "store_compliance_contract_passed",
                    "status": "pass",
                    "detail": "store compliance contract passed",
                },
                {
                    "id": "release_gate_local_runtime",
                    "status": "skip",
                    "detail": "runtime gate skipped",
                },
            ],
        }

    def test_evaluate_passes_when_fresh_and_required_checks_present(self) -> None:
        payload = self._valid_payload()
        passed, reasons, meta = evaluate_launch_signoff_artifact(
            payload,
            max_age_days=14,
            require_ready=False,
            now_utc=datetime(2026, 2, 22, 12, 0, tzinfo=UTC),
        )
        self.assertTrue(passed)
        self.assertEqual(reasons, [])
        self.assertFalse(meta["overall_ready"])

    def test_evaluate_fails_when_artifact_is_stale(self) -> None:
        payload = self._valid_payload()
        passed, reasons, _ = evaluate_launch_signoff_artifact(
            payload,
            max_age_days=1,
            require_ready=False,
            now_utc=datetime(2026, 2, 25, 0, 0, tzinfo=UTC),
        )
        self.assertFalse(passed)
        self.assertIn("artifact_stale", reasons)

    def test_evaluate_fails_when_required_check_is_missing(self) -> None:
        payload = self._valid_payload()
        payload["checks"] = payload["checks"][:-1]
        passed, reasons, _ = evaluate_launch_signoff_artifact(
            payload,
            max_age_days=14,
            require_ready=False,
            now_utc=datetime(2026, 2, 22, 1, 0, tzinfo=UTC),
        )
        self.assertFalse(passed)
        self.assertTrue(any(reason.startswith("missing_required_checks:") for reason in reasons))

    def test_evaluate_fails_when_require_ready_and_not_ready(self) -> None:
        payload = self._valid_payload()
        passed, reasons, _ = evaluate_launch_signoff_artifact(
            payload,
            max_age_days=14,
            require_ready=True,
            now_utc=datetime(2026, 2, 22, 1, 0, tzinfo=UTC),
        )
        self.assertFalse(passed)
        self.assertIn("overall_not_ready", reasons)

    def test_main_allows_missing_artifact_with_flag(self) -> None:
        exit_code = main(
            [
                "--allow-missing-artifact",
                "--artifact-path",
                "/tmp/non-existent-launch-signoff.json",
            ]
        )
        self.assertEqual(exit_code, 0)

    def test_main_fails_without_allow_missing_artifact(self) -> None:
        exit_code = main(["--artifact-path", "/tmp/non-existent-launch-signoff.json"])
        self.assertEqual(exit_code, 1)

    def test_main_writes_summary_file(self) -> None:
        payload = self._valid_payload()
        payload["overall_ready"] = True
        with tempfile.TemporaryDirectory() as tmp_dir:
            artifact_path = Path(tmp_dir) / "launch-signoff.json"
            summary_path = Path(tmp_dir) / "summary.json"
            artifact_path.write_text(json.dumps(payload), encoding="utf-8")

            exit_code = main(
                [
                    "--artifact-path",
                    str(artifact_path),
                    "--summary-path",
                    str(summary_path),
                    "--max-age-days",
                    "365",
                    "--require-ready",
                ]
            )

            self.assertEqual(exit_code, 0)
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["result"], "pass")
            self.assertEqual(summary["reasons"], [])


if __name__ == "__main__":
    unittest.main()
