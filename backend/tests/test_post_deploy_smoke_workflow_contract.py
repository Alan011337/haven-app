from __future__ import annotations

import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "post-deploy-smoke.yml"


class PostDeploySmokeWorkflowContractTests(unittest.TestCase):
    def test_workflow_runs_post_deploy_smoke_script(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("scripts/run_post_deploy_smoke.py", text)
        self.assertIn("post-deploy-smoke", text)
        self.assertIn("Open or Update Alert Issue", text)
        self.assertIn("POST_DEPLOY_BASE_URL", text)


if __name__ == "__main__":
    unittest.main()
