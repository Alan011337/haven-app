from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "monthly-incident-readiness.yml"


class MonthlyIncidentReadinessWorkflowContractTests(unittest.TestCase):
    def test_workflow_references_incident_runbooks_in_issue_body(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("docs/ops/incident-response-playbook.md", text)
        self.assertIn("docs/legal/data-rights.md", text)
        self.assertIn("RELEASE_CHECKLIST.md", text)

    def test_workflow_closes_stale_issue_when_readiness_recovers(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("Close stale readiness issue when passing", text)
        self.assertIn("state: \"closed\"", text)
        self.assertIn("Monthly readiness check is green. Closing this alert issue.", text)


if __name__ == "__main__":
    unittest.main()
