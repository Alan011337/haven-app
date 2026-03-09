from __future__ import annotations

import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "pre-commit-api-contract-check.sh"


class PreCommitApiContractScriptTests(unittest.TestCase):
    def test_script_contains_required_contract_checks(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("check_api_contract_snapshot.py", text)
        self.assertIn("check_api_contract_sot.py", text)
        self.assertIn("check_write_idempotency_coverage.py", text)
        self.assertIn("check_idempotency_normalization_contract.py", text)
        self.assertIn("generate-api-contract-types.mjs --check", text)


if __name__ == "__main__":
    unittest.main()
