from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_events_log_retention.py"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_events_log_retention", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover - defensive
    raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class EventsLogRetentionScriptTests(unittest.TestCase):
    def test_apply_requires_confirm_token(self) -> None:
        with patch("app.services.events_log_retention.cleanup_events_log") as mock_cleanup:
            rc = _MODULE.main(["--apply"])
        self.assertEqual(rc, 1)
        mock_cleanup.assert_not_called()

    def test_apply_aborts_when_batch_size_exceeds_cap(self) -> None:
        with patch(
            "app.services.events_log_retention.cleanup_events_log",
            return_value={
                "apply": False,
                "retention_days": 120,
                "batch_size": 6000,
                "cutoff_unix": 123456,
                "matched": 100,
                "purged": 0,
            },
        ) as mock_cleanup:
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-retention-apply",
                    "--max-apply-batch-size",
                    "5000",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertEqual(mock_cleanup.call_count, 1)

    def test_apply_aborts_when_matched_exceeds_cap(self) -> None:
        with patch(
            "app.services.events_log_retention.cleanup_events_log",
            return_value={
                "apply": False,
                "retention_days": 120,
                "batch_size": 1000,
                "cutoff_unix": 123456,
                "matched": 60000,
                "purged": 0,
            },
        ) as mock_cleanup:
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-retention-apply",
                    "--max-apply-matched",
                    "50000",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertEqual(mock_cleanup.call_count, 1)

    def test_apply_aborts_when_expected_cutoff_mismatch(self) -> None:
        with patch(
            "app.services.events_log_retention.cleanup_events_log",
            return_value={
                "apply": False,
                "retention_days": 120,
                "batch_size": 1000,
                "cutoff_unix": 123456,
                "matched": 1,
                "purged": 0,
            },
        ) as mock_cleanup:
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-retention-apply",
                    "--expected-cutoff-unix",
                    "999999",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertEqual(mock_cleanup.call_count, 1)

    def test_apply_runs_when_preflight_passes(self) -> None:
        with patch("app.services.events_log_retention.cleanup_events_log") as mock_cleanup:
            mock_cleanup.side_effect = [
                {
                    "apply": False,
                    "retention_days": 120,
                    "batch_size": 1000,
                    "cutoff_unix": 123456,
                    "matched": 10,
                    "purged": 0,
                },
                {
                    "apply": True,
                    "retention_days": 120,
                    "batch_size": 1000,
                    "cutoff_unix": 123456,
                    "matched": 10,
                    "purged": 10,
                },
            ]
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-retention-apply",
                    "--expected-cutoff-unix",
                    "123456",
                ]
            )

        self.assertEqual(rc, 0)
        self.assertEqual(mock_cleanup.call_count, 2)


if __name__ == "__main__":
    unittest.main()
