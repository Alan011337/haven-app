from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_with_timeout.py"


class RunWithTimeoutScriptTests(unittest.TestCase):
    def test_returns_124_when_timeout_exceeded(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--timeout-seconds",
                "1",
                "--heartbeat-seconds",
                "0",
                "--step-name",
                "slow_cmd",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(2)",
            ],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 124)
        self.assertIn("timeout", (proc.stdout + proc.stderr).lower())

    def test_emits_heartbeat_for_long_running_command(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--timeout-seconds",
                "5",
                "--heartbeat-seconds",
                "1",
                "--step-name",
                "heartbeat_cmd",
                "--",
                sys.executable,
                "-c",
                "import time; time.sleep(2)",
            ],
            cwd=str(BACKEND_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("heartbeat", (proc.stdout + proc.stderr).lower())


if __name__ == "__main__":
    unittest.main()
