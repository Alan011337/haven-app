from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_ai_router_multinode_stress.py"


class AIRouterMultinodeStressScriptTests(unittest.TestCase):
    def test_contract_mode_with_empty_modes_finishes_without_pytest(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "summary.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "--modes",
                    "",
                    "--runs",
                    "1",
                    "--output",
                    str(output),
                ],
                cwd=str(BACKEND_ROOT),
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["result"], "pass")
            self.assertEqual(payload["meta"]["total_executions"], 0)


if __name__ == "__main__":
    unittest.main()
