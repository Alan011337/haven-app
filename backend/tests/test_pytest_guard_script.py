from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "pytest_guard.py"
pytestmark = [pytest.mark.unit]


class PytestGuardScriptTests(unittest.TestCase):
    def _guard_env(self) -> dict[str, str]:
        env = dict(os.environ)
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        return env

    def test_pytest_guard_returns_124_when_timeout_exceeded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "test_slow.py"
            test_path.write_text(
                textwrap.dedent(
                    """
                    import time

                    def test_slow():
                        time.sleep(2)
                    """
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--timeout-seconds",
                    "1",
                    "--",
                    "-p",
                    "no:cacheprovider",
                    str(test_path),
                ],
                cwd=str(BACKEND_ROOT),
                capture_output=True,
                env=self._guard_env(),
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 124)
            self.assertIn("timeout", (result.stdout + result.stderr).lower())

    def test_pytest_guard_emits_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            test_path = Path(tmp_dir) / "test_wait.py"
            test_path.write_text(
                textwrap.dedent(
                    """
                    import time

                    def test_wait():
                        time.sleep(2)
                    """
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--timeout-seconds",
                    "5",
                    "--heartbeat-seconds",
                    "1",
                    "--",
                    "-p",
                    "no:cacheprovider",
                    str(test_path),
                ],
                cwd=str(BACKEND_ROOT),
                capture_output=True,
                env=self._guard_env(),
                text=True,
                timeout=20,
            )
            self.assertIn(result.returncode, {0, 124})
            self.assertIn("heartbeat", (result.stdout + result.stderr).lower())

    def test_pytest_guard_kills_child_process_group_on_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            pid_path = Path(tmp_dir) / "child.pid"
            test_path = Path(tmp_dir) / "test_child.py"
            test_path.write_text(
                textwrap.dedent(
                    f"""
                    import pathlib
                    import subprocess
                    import sys
                    import time

                    def test_child():
                        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(20)"])
                        pathlib.Path(r"{pid_path}").write_text(str(proc.pid), encoding="utf-8")
                        time.sleep(20)
                    """
                ),
                encoding="utf-8",
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--timeout-seconds",
                    "2",
                    "--graceful-terminate-seconds",
                    "1",
                    "--heartbeat-seconds",
                    "0",
                    "--",
                    "-p",
                    "no:cacheprovider",
                    str(test_path),
                ],
                cwd=str(BACKEND_ROOT),
                capture_output=True,
                env=self._guard_env(),
                text=True,
                timeout=25,
            )
            self.assertEqual(result.returncode, 124)
            if pid_path.exists():
                child_pid = int(pid_path.read_text(encoding="utf-8").strip())
                deadline = time.time() + 3.0
                alive = False
                while time.time() < deadline:
                    try:
                        import os

                        os.kill(child_pid, 0)
                        alive = True
                        time.sleep(0.1)
                    except OSError:
                        alive = False
                        break
                self.assertFalse(alive, "child process should be terminated by pytest_guard timeout")


if __name__ == "__main__":
    unittest.main()
