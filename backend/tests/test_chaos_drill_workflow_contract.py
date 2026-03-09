import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "chaos-drill.yml"


class ChaosDrillWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_with_weekly_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Chaos Drill", text)
        self.assertIn('cron: "0 9 * * 5"', text)

    def test_workflow_runs_drill_and_validates_evidence(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_chaos_drill_audit.py", text)
        self.assertIn("--kind chaos-drill --contract-mode strict", text)
        self.assertIn("chaos-drill-evidence", text)


if __name__ == "__main__":
    unittest.main()
