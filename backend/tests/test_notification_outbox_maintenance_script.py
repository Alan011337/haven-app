from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_notification_outbox_maintenance.py"


class NotificationOutboxMaintenanceScriptTests(unittest.TestCase):
    def test_script_writes_dry_run_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_path = Path(tmp_dir) / "outbox-maintenance.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--dry-run",
                    "--output",
                    str(output_path),
                ],
                cwd=str(BACKEND_ROOT),
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(result.returncode, 0, msg=f"{result.stdout}\n{result.stderr}")
            self.assertTrue(output_path.exists())
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertTrue(payload.get("dry_run"))
            self.assertIn("before", payload)
            self.assertIn("after", payload)
            self.assertIn("actions", payload)


if __name__ == "__main__":
    unittest.main()
