import importlib.util
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_ai_quality_snapshot_freshness_gate.py"
_SPEC = importlib.util.spec_from_file_location("check_ai_quality_snapshot_freshness_gate", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def _snapshot_payload(*, generated_at: datetime, result: str) -> dict:
    return {
        "artifact_kind": "ai-quality-snapshot",
        "schema_version": "1.0.0",
        "generated_at": generated_at.isoformat().replace("+00:00", "Z"),
        "evaluation": {
            "result": result,
            "degraded_reasons": ["drift_score_above_max"] if result == "degraded" else [],
        },
    }


class AIQualitySnapshotFreshnessGateTests(unittest.TestCase):
    def test_fresh_pass_payload_succeeds(self) -> None:
        now = datetime.now(UTC)
        passed, result, reasons, meta = _MODULE.evaluate_ai_quality_snapshot(
            _snapshot_payload(generated_at=now - timedelta(hours=2), result="pass"),
            max_age_hours=36.0,
            require_pass=False,
            now_utc=now,
        )
        self.assertTrue(passed)
        self.assertEqual(result, "pass")
        self.assertEqual(reasons, [])
        self.assertIn("age_hours", meta)

    def test_degraded_payload_is_non_blocking_by_default(self) -> None:
        now = datetime.now(UTC)
        passed, result, reasons, meta = _MODULE.evaluate_ai_quality_snapshot(
            _snapshot_payload(generated_at=now - timedelta(hours=1), result="degraded"),
            max_age_hours=36.0,
            require_pass=False,
            now_utc=now,
        )
        self.assertTrue(passed)
        self.assertEqual(result, "degraded")
        self.assertEqual(reasons, [])
        self.assertEqual(meta["evaluation_result"], "degraded")

    def test_stale_payload_fails(self) -> None:
        now = datetime.now(UTC)
        passed, result, reasons, _ = _MODULE.evaluate_ai_quality_snapshot(
            _snapshot_payload(generated_at=now - timedelta(hours=48), result="pass"),
            max_age_hours=24.0,
            require_pass=False,
            now_utc=now,
        )
        self.assertFalse(passed)
        self.assertEqual(result, "fail")
        self.assertIn("evidence_stale", reasons)

    def test_script_allows_missing_evidence_when_flag_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.json"
            exit_code = _MODULE.main(
                [
                    "--evidence",
                    str(missing_path),
                    "--allow-missing-evidence",
                ]
            )
        self.assertEqual(exit_code, 0)

    def test_script_fails_on_missing_evidence_without_allow_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing_path = Path(tmpdir) / "missing.json"
            exit_code = _MODULE.main(
                [
                    "--evidence",
                    str(missing_path),
                ]
            )
        self.assertEqual(exit_code, 1)

    def test_script_fails_when_require_pass_and_snapshot_is_degraded(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            evidence_path = Path(tmpdir) / "snapshot.json"
            payload = _snapshot_payload(
                generated_at=datetime.now(UTC) - timedelta(hours=1),
                result="degraded",
            )
            evidence_path.write_text(json.dumps(payload), encoding="utf-8")
            exit_code = _MODULE.main(
                [
                    "--evidence",
                    str(evidence_path),
                    "--require-pass",
                ]
            )
        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
