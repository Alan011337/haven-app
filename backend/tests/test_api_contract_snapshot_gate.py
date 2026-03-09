from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_api_contract_snapshot.py"


class ApiContractSnapshotGateTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT_PATH), *args],
            cwd=str(BACKEND_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )

    def test_snapshot_write_then_check_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "api-contract-snapshot.json"
            write_proc = self._run("--snapshot-path", str(snapshot_path), "--write")
            self.assertEqual(write_proc.returncode, 0, write_proc.stderr)
            self.assertTrue(snapshot_path.exists())

            check_proc = self._run("--snapshot-path", str(snapshot_path))
            self.assertEqual(check_proc.returncode, 0, check_proc.stdout)
            self.assertIn("ok: contract snapshot matches", check_proc.stdout)

    def test_snapshot_check_fails_on_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            snapshot_path = Path(tmp_dir) / "api-contract-snapshot.json"
            write_proc = self._run("--snapshot-path", str(snapshot_path), "--write")
            self.assertEqual(write_proc.returncode, 0, write_proc.stderr)

            payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
            payload["route_count"] = int(payload.get("route_count", 0)) + 1
            snapshot_path.write_text(
                json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )

            check_proc = self._run("--snapshot-path", str(snapshot_path))
            self.assertEqual(check_proc.returncode, 1)
            self.assertIn("contract drift detected", check_proc.stdout)


if __name__ == "__main__":
    unittest.main()
