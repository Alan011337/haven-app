import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "backup-restore-drill.yml"


class BackupRestoreDrillWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_with_quarterly_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Backup Restore Drill", text)
        self.assertIn('cron: "0 4 1 */3 *"', text)

    def test_workflow_runs_drill_and_validates_evidence(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_backup_restore_drill_audit.py", text)
        self.assertIn("--kind backup-restore-drill --contract-mode strict", text)
        self.assertIn("backup-restore-drill-evidence", text)


if __name__ == "__main__":
    unittest.main()
