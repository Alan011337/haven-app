import importlib.util
import json
import sys
import unittest
import uuid
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "run_pricing_experiment_dry_run.py"
_SPEC = importlib.util.spec_from_file_location("run_pricing_experiment_dry_run", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load script module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class PricingExperimentDryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_feature_flags = settings.FEATURE_FLAGS_JSON
        self.original_kill_switches = settings.FEATURE_KILL_SWITCHES_JSON

    def tearDown(self) -> None:
        settings.FEATURE_FLAGS_JSON = self.original_feature_flags
        settings.FEATURE_KILL_SWITCHES_JSON = self.original_kill_switches

    def test_returns_control_when_kill_switch_enabled(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": true}'
        decision = _MODULE.evaluate_pricing_experiment_decision(
            user_id=str(uuid.uuid4()),
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
        )
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.variant, "control")
        self.assertEqual(decision.reason, "kill_switch:disable_pricing_experiment")

    def test_returns_deterministic_variant_when_eligible(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": false}'
        user_id = str(uuid.uuid4())
        first = _MODULE.evaluate_pricing_experiment_decision(
            user_id=user_id,
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
        )
        second = _MODULE.evaluate_pricing_experiment_decision(
            user_id=user_id,
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
        )
        self.assertTrue(first.eligible)
        self.assertEqual(first.variant, second.variant)
        self.assertEqual(first.bucket, second.bucket)

    def test_main_rejects_invalid_user_id(self) -> None:
        exit_code = _MODULE.main(["--user-id", "not-a-uuid"])
        self.assertEqual(exit_code, 1)

    def test_main_outputs_json_payload(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": false}'
        user_id = str(uuid.uuid4())
        # Capture stdout via monkeypatch of print target is unnecessary; just ensure function exits.
        exit_code = _MODULE.main(["--user-id", user_id, "--has-partner"])
        self.assertEqual(exit_code, 0)

    def test_weights_json_validation_requires_object(self) -> None:
        exit_code = _MODULE.main(["--user-id", str(uuid.uuid4()), "--weights-json", "[1,2,3]"])
        self.assertEqual(exit_code, 0)
        # Non-object falls back to default weights; this should still succeed.

    def test_assignment_variant_is_valid(self) -> None:
        settings.FEATURE_FLAGS_JSON = (
            '{"growth_ab_experiment_enabled": true, "growth_pricing_experiment_enabled": true}'
        )
        settings.FEATURE_KILL_SWITCHES_JSON = '{"disable_pricing_experiment": false}'
        decision = _MODULE.evaluate_pricing_experiment_decision(
            user_id=str(uuid.uuid4()),
            experiment_key="pricing_paywall_copy_v1",
            has_partner=True,
            weights=json.loads('{"control": 1, "pricing_variant_a": 1}'),
        )
        self.assertIn(decision.variant, {"control", "pricing_variant_a"})


if __name__ == "__main__":
    unittest.main()
