from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_events_log_rollup.py"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_events_log_rollup", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:  # pragma: no cover
    raise RuntimeError(f"Failed to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class EventsLogRollupScriptTests(unittest.TestCase):
    def test_apply_requires_confirm_token(self) -> None:
        with patch("app.services.events_log_rollup.rollup_events_log_daily") as mock_rollup:
            rc = _MODULE.main(["--apply"])
        self.assertEqual(rc, 1)
        mock_rollup.assert_not_called()

    def test_apply_runs_with_confirm_token(self) -> None:
        with patch(
            "app.services.events_log_rollup.rollup_events_log_daily",
            return_value={
                "apply": True,
                "enabled": True,
                "retention_days": 30,
                "batch_size": 100,
                "cutoff_unix": 1,
                "matched": 10,
                "selected": 10,
                "rolled_up_rows": 3,
                "purged": 10,
            },
        ) as mock_rollup:
            rc = _MODULE.main(["--apply", "--confirm-apply", "events-log-rollup-apply"])
        self.assertEqual(rc, 0)
        mock_rollup.assert_called_once()


if __name__ == "__main__":
    unittest.main()
