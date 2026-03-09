import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "growth-nsm-snapshot.yml"


class GrowthNsmSnapshotWorkflowContractTests(unittest.TestCase):
    def test_daily_workflow_exists_with_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Growth NSM Snapshot", text)
        self.assertIn("schedule:", text)
        self.assertIn('cron: "20 3 * * *"', text)
        self.assertIn("name: Generate Growth NSM WRM snapshot evidence", text)

    def test_daily_workflow_runs_snapshot_script_and_uploads_artifact(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_growth_nsm_snapshot.py", text)
        self.assertIn("--output docs/growth/evidence/wrm-snapshot-${GITHUB_RUN_ID}.json", text)
        self.assertIn("--latest-path docs/growth/evidence/wrm-snapshot-latest.json", text)
        self.assertIn("name: Growth NSM snapshot summary", text)
        self.assertIn("name: Upload Growth NSM snapshot artifact", text)
        self.assertIn("name: growth-nsm-snapshot", text)


if __name__ == "__main__":
    unittest.main()
