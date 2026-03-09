import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
P0_READINESS_SCRIPT_PATH = REPO_ROOT / "scripts" / "p0-readiness-audit.sh"


class P0ReadinessAuditContractTests(unittest.TestCase):
    def test_store_compliance_contract_check_is_included(self) -> None:
        text = P0_READINESS_SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn('"store_compliance_contract_passed"', text)
        self.assertIn("check_store_compliance_contract.py", text)
        self.assertIn("store compliance contract passed (BILL-STORE-01)", text)


if __name__ == "__main__":
    unittest.main()
