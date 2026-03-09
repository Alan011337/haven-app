from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_notification_outbox_health_snapshot.py"


class NotificationOutboxHealthSnapshotScriptTests(unittest.TestCase):
    def test_builds_snapshot_from_local_health_payload(self) -> None:
        payload = {
            "status": "degraded",
            "degraded_reasons": ["notification_outbox_depth_high", "ws_sli_below_target"],
            "checks": {
                "notification_outbox_status": {"status": "degraded"},
                "notification_outbox_depth": 18,
                "notification_outbox_oldest_pending_age_seconds": 120,
                "notification_outbox_retry_age_p95_seconds": 33,
                "notification_outbox_dead_letter_rate": 0.25,
                "notification_outbox_stale_processing_count": 2,
                "notification_outbox_dispatch_lock_heartbeat_age_seconds": 8,
            },
        }

        with tempfile.TemporaryDirectory() as td:
            health_file = Path(td) / "health.json"
            output_file = Path(td) / "snapshot.json"
            health_file.write_text(json.dumps(payload), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--health-file",
                    str(health_file),
                    "--output",
                    str(output_file),
                ],
                cwd=str(BACKEND_ROOT),
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            snapshot = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(snapshot.get("health_status"), "degraded")
            self.assertEqual(snapshot.get("outbox", {}).get("depth"), 18)
            self.assertEqual(
                snapshot.get("degraded_reasons"),
                ["notification_outbox_depth_high"],
            )


if __name__ == "__main__":
    unittest.main()

