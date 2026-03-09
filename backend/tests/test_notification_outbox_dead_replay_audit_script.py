from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_notification_outbox_dead_replay_audit.py"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

_SPEC = importlib.util.spec_from_file_location("run_notification_outbox_dead_replay_audit", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


class NotificationOutboxDeadReplayAuditScriptTests(unittest.TestCase):
    def test_dry_run_writes_summary_without_replay_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "dead-replay.json"
            with patch(
                "app.services.notification_outbox.get_notification_outbox_status_counts",
                side_effect=[
                    {"pending": 1, "retry": 2, "processing": 0, "sent": 10, "dead": 8},
                    {"pending": 1, "retry": 2, "processing": 0, "sent": 10, "dead": 8},
                ],
            ), patch(
                "app.services.notification_outbox.get_notification_outbox_dead_letter_rate",
                side_effect=[0.4, 0.4],
            ), patch(
                "app.services.notification_outbox.replay_dead_notification_outbox"
            ) as replay:
                rc = _MODULE.main(["--output", str(output)])

            self.assertEqual(rc, 0)
            replay.assert_not_called()
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "dry_run")
            self.assertEqual(payload["replay"]["replayed"], 0)
            self.assertEqual(payload["before"]["dead"], 8)

    def test_apply_mode_calls_replay_and_persists_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output = Path(tmp_dir) / "dead-replay.json"
            with patch(
                "app.services.notification_outbox.get_notification_outbox_status_counts",
                side_effect=[
                    {"pending": 0, "retry": 1, "processing": 0, "sent": 12, "dead": 5},
                    {"pending": 0, "retry": 3, "processing": 0, "sent": 12, "dead": 2},
                ],
            ), patch(
                "app.services.notification_outbox.get_notification_outbox_dead_letter_rate",
                side_effect=[0.25, 0.1],
            ), patch(
                "app.services.notification_outbox.replay_dead_notification_outbox",
                return_value={"selected": 3, "replayed": 3, "errors": 0},
            ) as replay:
                rc = _MODULE.main(
                    ["--apply", "--replay-limit", "3", "--reset-attempt-count", "--output", str(output)]
                )

            self.assertEqual(rc, 0)
            replay.assert_called_once()
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "apply")
            self.assertEqual(payload["replay"]["selected"], 3)
            self.assertEqual(payload["replay"]["replayed"], 3)
            self.assertEqual(payload["after"]["dead"], 2)


if __name__ == "__main__":
    unittest.main()
