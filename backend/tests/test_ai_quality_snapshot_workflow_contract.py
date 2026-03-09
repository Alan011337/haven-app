import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

AI_QUALITY_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "ai-quality-snapshot.yml"


class AIQualitySnapshotWorkflowContractTests(unittest.TestCase):
    def test_daily_workflow_exists_with_schedule(self) -> None:
        text = AI_QUALITY_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: AI Quality Snapshot", text)
        self.assertIn("schedule:", text)
        self.assertIn('cron: "5 3 * * *"', text)
        self.assertIn("permissions:", text)
        self.assertIn("issues: write", text)

    def test_daily_workflow_generates_and_validates_snapshot(self) -> None:
        text = AI_QUALITY_WORKFLOW_PATH.read_text(encoding="utf-8")
        self.assertIn("name: Generate AI quality snapshot evidence", text)
        self.assertIn("name: Validate AI quality snapshot freshness contract", text)
        self.assertIn("name: Run AI eval drift detector", text)
        self.assertIn("python scripts/run_ai_quality_snapshot.py", text)
        self.assertIn("python scripts/run_ai_eval_drift_detector.py", text)
        self.assertIn("--output docs/security/evidence/ai-quality-snapshot-${GITHUB_RUN_ID}.json", text)
        self.assertIn("--latest-path docs/security/evidence/ai-quality-snapshot-latest.json", text)
        self.assertIn("--output docs/security/evidence/ai-eval-drift-${GITHUB_RUN_ID}.json", text)
        self.assertIn("--latest-path docs/security/evidence/ai-eval-drift-latest.json", text)
        self.assertIn(
            "python scripts/check_ai_quality_snapshot_freshness_gate.py --evidence docs/security/evidence/ai-quality-snapshot-latest.json --max-age-hours 36 --summary-path /tmp/ai-quality-snapshot-gate-summary.json",
            text,
        )
        self.assertIn("name: AI eval drift summary", text)
        self.assertIn("name: Detect degraded AI quality snapshot", text)
        self.assertIn("name: Detect AI eval drift alert", text)
        self.assertIn("name: Open or update degraded AI quality issue", text)
        self.assertIn("name: Close degraded AI quality issue when recovered", text)
        self.assertIn("name: Open or update AI eval drift alert issue", text)
        self.assertIn("name: Close AI eval drift alert issue when recovered", text)
        self.assertIn("steps.degrade_flag.outputs.degraded == 'true'", text)
        self.assertIn("steps.degrade_flag.outputs.degraded != 'true'", text)
        self.assertIn("steps.drift_flag.outputs.drift_alert == 'true'", text)
        self.assertIn("steps.drift_flag.outputs.drift_alert != 'true'", text)
        self.assertIn("name: Upload AI quality snapshot artifact", text)
        self.assertIn("docs/security/evidence/ai-eval-drift-*.json", text)
        self.assertIn("/tmp/ai-eval-drift-summary.json", text)


if __name__ == "__main__":
    unittest.main()
