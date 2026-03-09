import sys
import unittest
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.pricing_experiment_runtime import (  # noqa: E402
    evaluate_pricing_experiment_decision,
    evaluate_pricing_experiment_guardrails,
    pricing_experiment_runtime_metrics,
)


class PricingExperimentRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON
        pricing_experiment_runtime_metrics.reset()

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches
        pricing_experiment_runtime_metrics.reset()

    def test_assignment_is_deterministic_when_flags_enabled(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": false}'

        user_id = str(uuid.uuid4())
        first = evaluate_pricing_experiment_decision(
            user_id=user_id,
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
        )
        second = evaluate_pricing_experiment_decision(
            user_id=user_id,
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
        )

        self.assertTrue(first.eligible)
        self.assertEqual(first.variant, second.variant)
        self.assertEqual(first.bucket, second.bucket)

        snapshot = pricing_experiment_runtime_metrics.snapshot()
        self.assertEqual(snapshot["counts"]["pricing_experiment_assignment_total"], 2)

    def test_assignment_falls_back_to_control_on_experiment_key_mismatch(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": false}'

        decision = evaluate_pricing_experiment_decision(
            user_id=str(uuid.uuid4()),
            experiment_key="unexpected_experiment_key",
            has_partner=True,
        )

        self.assertFalse(decision.eligible)
        self.assertEqual(decision.variant, "control")
        self.assertEqual(decision.reason, "experiment_key_mismatch")

    def test_guardrail_evaluation_triggers_when_metric_exceeds_threshold(self) -> None:
        result = evaluate_pricing_experiment_guardrails(
            metric_values={
                "pricing.experiment.refund_rate": 0.2,
                "pricing.experiment.chargeback_rate": 0.001,
                "pricing.experiment.p0_cuj_failure_rate": 0.0001,
                "pricing.experiment.support_ticket_rate": 0.01,
            }
        )

        self.assertEqual(result["status"], "triggered")
        self.assertEqual(len(result["breaches"]), 1)
        self.assertEqual(result["breaches"][0]["metric"], "pricing.experiment.refund_rate")

        snapshot = pricing_experiment_runtime_metrics.snapshot()
        self.assertEqual(snapshot["counts"]["pricing_experiment_guardrail_evaluations_total"], 1)
        self.assertEqual(snapshot["counts"]["pricing_experiment_guardrail_triggered_total"], 1)
        self.assertEqual(snapshot["guardrail_breach_counts"]["pricing.experiment.refund_rate"], 1)

    def test_guardrail_evaluation_returns_insufficient_data_when_all_metrics_missing(self) -> None:
        result = evaluate_pricing_experiment_guardrails(metric_values={})
        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(len(result["missing_metrics"]), 4)


if __name__ == "__main__":
    unittest.main()
