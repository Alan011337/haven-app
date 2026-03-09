import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pricing-experiment-guardrail.yml"


class PricingExperimentGuardrailWorkflowContractTests(unittest.TestCase):
    def test_workflow_exists_with_daily_schedule(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Pricing Experiment Guardrail Snapshot", text)
        self.assertIn("schedule:", text)
        self.assertIn('cron: "35 3 * * *"', text)

    def test_workflow_runs_guardrail_snapshot_script_and_uploads_artifact(self) -> None:
        text = WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("python scripts/run_pricing_experiment_guardrail_snapshot.py", text)
        self.assertIn("--allow-missing-metrics", text)
        self.assertIn("--output docs/security/evidence/pricing-experiment-guardrail-${GITHUB_RUN_ID}.json", text)
        self.assertIn("--latest-path docs/security/evidence/pricing-experiment-guardrail-latest.json", text)
        self.assertIn("name: Upload pricing experiment guardrail artifact", text)
        self.assertIn("name: pricing-experiment-guardrail", text)


if __name__ == "__main__":
    unittest.main()
