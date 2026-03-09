import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_supply_chain_workflow_contract.py"
WORKFLOW_PATH = BACKEND_ROOT.parent / ".github" / "workflows" / "supply-chain-security.yml"


class SupplyChainWorkflowContractTests(unittest.TestCase):
    def test_script_checks_expected_markers(self) -> None:
        text = SCRIPT_PATH.read_text(encoding="utf-8")
        self.assertIn("supply-chain-security.yml", text)
        self.assertIn("pip-audit", text)
        self.assertIn("npm audit", text)
        self.assertIn("gitleaks", text)

    def test_workflow_contains_required_jobs(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("backend-dependency-audit", text)
        self.assertIn("frontend-dependency-audit", text)
        self.assertIn("secret-scan", text)


if __name__ == "__main__":
    unittest.main()
