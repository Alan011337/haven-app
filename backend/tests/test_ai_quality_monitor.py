import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_quality_monitor import (  # noqa: E402
    AIQualityThresholds,
    calculate_relative_drift_score,
    evaluate_quality_gate,
)


class AIQualityMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.thresholds = AIQualityThresholds(
            schema_compliance_min=99.9,
            hallucination_proxy_max=0.05,
            drift_score_max=0.2,
            cost_usd_per_active_couple_max=1.5,
        )

    def test_calculate_relative_drift_score_is_zero_for_equal_snapshots(self) -> None:
        baseline = {
            "schema_compliance_rate": 99.95,
            "hallucination_proxy_rate": 0.02,
            "estimated_cost_usd_per_active_couple": 0.9,
            "avg_tokens_per_analysis": 850.0,
        }
        drift_score = calculate_relative_drift_score(
            baseline=baseline,
            current=dict(baseline),
            keys=(
                "schema_compliance_rate",
                "hallucination_proxy_rate",
                "estimated_cost_usd_per_active_couple",
                "avg_tokens_per_analysis",
            ),
        )
        self.assertEqual(drift_score, 0.0)

    def test_evaluate_quality_gate_passes_for_healthy_snapshot(self) -> None:
        baseline = {
            "schema_compliance_rate": 99.95,
            "hallucination_proxy_rate": 0.02,
            "estimated_cost_usd_per_active_couple": 0.9,
            "avg_tokens_per_analysis": 850.0,
        }
        current = {
            "schema_compliance_rate": 99.93,
            "hallucination_proxy_rate": 0.03,
            "estimated_cost_usd_per_active_couple": 1.1,
            "avg_tokens_per_analysis": 900.0,
        }
        result = evaluate_quality_gate(
            baseline=baseline,
            current=current,
            thresholds=self.thresholds,
        )
        self.assertEqual(result["result"], "pass")
        self.assertEqual(result["degraded_reasons"], [])
        self.assertEqual(result["deterministic_gate_actions"], [])
        self.assertEqual(result["request_class_gate"]["journal_analysis"], "green")

    def test_evaluate_quality_gate_flags_regressions(self) -> None:
        baseline = {
            "schema_compliance_rate": 99.95,
            "hallucination_proxy_rate": 0.02,
            "estimated_cost_usd_per_active_couple": 0.9,
            "avg_tokens_per_analysis": 850.0,
        }
        current = {
            "schema_compliance_rate": 98.5,
            "hallucination_proxy_rate": 0.08,
            "estimated_cost_usd_per_active_couple": 2.1,
            "avg_tokens_per_analysis": 1600.0,
        }
        result = evaluate_quality_gate(
            baseline=baseline,
            current=current,
            thresholds=self.thresholds,
        )
        self.assertEqual(result["result"], "degraded")
        self.assertIn("schema_compliance_below_min", result["degraded_reasons"])
        self.assertIn("hallucination_proxy_above_max", result["degraded_reasons"])
        self.assertIn("cost_per_active_couple_above_max", result["degraded_reasons"])
        self.assertIn("drift_score_above_max", result["degraded_reasons"])
        self.assertIn("switch_to_lower_cost_profile", result["deterministic_gate_actions"])
        self.assertIn("prefer_stable_profile", result["deterministic_gate_actions"])
        self.assertEqual(result["request_class_gate"]["journal_analysis"], "red")


if __name__ == "__main__":
    unittest.main()
