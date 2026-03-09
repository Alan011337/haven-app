from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "data-retention-weekly.yml"


class DataRetentionWeeklyWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_with_schedule_and_dispatch(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Data Retention Weekly", text)
        self.assertIn("workflow_dispatch", text)
        self.assertIn("schedule:", text)

    def test_workflow_runs_retention_bundle_and_uploads_artifact(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_data_retention_bundle.py", text)
        self.assertIn("/tmp/data-retention-bundle-weekly-summary.json", text)
        self.assertIn("name: data-retention-weekly", text)
        self.assertIn("Open or Update Alert Issue", text)


if __name__ == "__main__":
    unittest.main()
