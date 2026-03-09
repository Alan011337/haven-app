import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "growth-activation-funnel-snapshot.yml"


class GrowthActivationSnapshotWorkflowContractTests(unittest.TestCase):
    def test_daily_workflow_exists_with_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Growth Activation Funnel Snapshot", text)
        self.assertIn("schedule:", text)
        self.assertIn('cron: "45 3 * * *"', text)
        self.assertIn("name: Generate growth activation funnel snapshot evidence", text)

    def test_daily_workflow_runs_snapshot_script_and_uploads_artifact(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_growth_activation_funnel_snapshot.py", text)
        self.assertIn(
            "--output docs/growth/evidence/activation-funnel-snapshot-${GITHUB_RUN_ID}.json",
            text,
        )
        self.assertIn(
            "--latest-path docs/growth/evidence/activation-funnel-snapshot-latest.json",
            text,
        )
        self.assertIn("name: Growth activation funnel snapshot summary", text)
        self.assertIn("name: Upload growth activation funnel snapshot artifact", text)
        self.assertIn("name: growth-activation-funnel-snapshot", text)


if __name__ == "__main__":
    unittest.main()
