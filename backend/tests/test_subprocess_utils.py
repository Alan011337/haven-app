from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from scripts._subprocess_utils import run_command_with_timeout


class SubprocessUtilsTests(unittest.TestCase):
    def test_run_command_with_timeout_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = run_command_with_timeout(
                command=[sys.executable, "-c", "print('ok')"],
                cwd=Path(td),
                timeout_seconds=5,
            )
            self.assertEqual(result["exit_code"], 0)
            self.assertIn("ok", result["stdout"])
            self.assertFalse(result["timeout"])

    def test_run_command_with_timeout_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = run_command_with_timeout(
                command=[sys.executable, "-c", "import time; time.sleep(2)"],
                cwd=Path(td),
                timeout_seconds=1,
            )
            self.assertEqual(result["exit_code"], 124)
            self.assertTrue(result["timeout"])


if __name__ == "__main__":
    unittest.main()
