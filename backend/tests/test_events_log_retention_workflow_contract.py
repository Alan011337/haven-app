from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "events-log-retention-drill.yml"


class EventsLogRetentionWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_and_is_scheduled(self) -> None:
        self.assertTrue(WORKFLOW_PATH.exists(), "events retention drill workflow must exist")
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn('cron: "0 3 1 * *"', text)
        self.assertIn("workflow_dispatch:", text)

    def test_workflow_runs_retention_script_and_uploads_artifact(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_events_log_lifecycle.py", text)
        self.assertIn("--rollup-retention-days", text)
        self.assertIn("--rollup-batch-size", text)
        self.assertIn("--retention-days", text)
        self.assertIn("--retention-batch-size", text)
        self.assertIn("artifact_kind\": \"events-log-retention-drill\"", text)
        self.assertIn("governance_mode\": \"rollup_then_retention\"", text)
        self.assertIn("name: events-log-retention-drill", text)


if __name__ == "__main__":
    unittest.main()
