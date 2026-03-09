import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "billing-console-drift.yml"


class BillingConsoleDriftWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_with_daily_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Billing Console Drift", text)
        self.assertIn('cron: "0 5 * * *"', text)

    def test_workflow_runs_audit_and_validates_evidence(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_billing_console_drift_audit.py", text)
        self.assertIn("--kind billing-console-drift --contract-mode strict", text)
        self.assertIn("billing-console-drift-evidence", text)


if __name__ == "__main__":
    unittest.main()
