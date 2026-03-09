from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_events_log_lifecycle.py"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_events_log_lifecycle", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class EventsLogLifecycleScriptTests(unittest.TestCase):
    def test_apply_requires_confirm_token(self) -> None:
        with patch("app.services.events_log_rollup.rollup_events_log_daily") as mock_rollup, patch(
            "app.services.events_log_retention.cleanup_events_log"
        ) as mock_retention:
            mock_rollup.return_value = {"selected": 0, "apply": False}
            mock_retention.return_value = {"matched": 0, "apply": False}
            rc = _MODULE.main(["--apply"])
        self.assertEqual(rc, 1)
        self.assertEqual(mock_rollup.call_count, 1)
        self.assertEqual(mock_retention.call_count, 1)

    def test_apply_aborts_when_rollup_preflight_exceeds_cap(self) -> None:
        with patch(
            "app.services.events_log_rollup.rollup_events_log_daily",
            return_value={"selected": 200, "apply": False},
        ) as mock_rollup, patch(
            "app.services.events_log_retention.cleanup_events_log",
            return_value={"matched": 10, "apply": False},
        ) as mock_retention:
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-lifecycle-apply",
                    "--max-apply-rollup-selected",
                    "100",
                ]
            )
        self.assertEqual(rc, 1)
        self.assertEqual(mock_rollup.call_count, 1)
        self.assertEqual(mock_retention.call_count, 1)

    def test_apply_runs_rollup_then_retention(self) -> None:
        calls: list[str] = []

        def _mock_rollup(*, apply: bool, **kwargs):  # noqa: ARG001
            calls.append(f"rollup:{'apply' if apply else 'dry_run'}")
            if apply:
                return {"apply": True, "selected": 1, "rolled_up_rows": 1, "purged": 1}
            return {"apply": False, "selected": 1}

        def _mock_retention(*, apply: bool, **kwargs):  # noqa: ARG001
            calls.append(f"retention:{'apply' if apply else 'dry_run'}")
            if apply:
                return {"apply": True, "matched": 1, "purged": 1}
            return {"apply": False, "matched": 1}

        with patch("app.services.events_log_rollup.rollup_events_log_daily", side_effect=_mock_rollup), patch(
            "app.services.events_log_retention.cleanup_events_log", side_effect=_mock_retention
        ):
            rc = _MODULE.main(
                [
                    "--apply",
                    "--confirm-apply",
                    "events-log-lifecycle-apply",
                    "--max-apply-rollup-selected",
                    "1000",
                    "--max-apply-retention-matched",
                    "1000",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(
            calls,
            [
                "rollup:dry_run",
                "retention:dry_run",
                "rollup:apply",
                "retention:apply",
            ],
        )


if __name__ == "__main__":
    unittest.main()
