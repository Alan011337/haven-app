from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_idempotency_normalization_contract.py"


class IdempotencyNormalizationContractScriptTests(unittest.TestCase):
    def test_contract_script_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(SCRIPT_PATH)],
            cwd=str(BACKEND_ROOT),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, msg=proc.stderr or proc.stdout)
        self.assertIn("result: pass", proc.stdout)


if __name__ == "__main__":
    unittest.main()

