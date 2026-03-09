import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_pricing_experiment_policy_contract.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_pricing_experiment_policy_contract",
    POLICY_SCRIPT_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class PricingExperimentPolicyContractTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_pricing_experiment_policy_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_required_flag(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["feature_flags"]["required"] = ["growth_ab_experiment_enabled"]
        violations = _MODULE.collect_pricing_experiment_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_required_flag" for v in violations))

    def test_policy_rejects_missing_guardrail_metric(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["guardrail_metrics"] = ["pricing.experiment.refund_rate"]
        violations = _MODULE.collect_pricing_experiment_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_guardrail_metric" for v in violations))

    def test_policy_rejects_missing_reference(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"].pop("dry_run_script", None)
        violations = _MODULE.collect_pricing_experiment_policy_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_reference" for v in violations))


if __name__ == "__main__":
    unittest.main()
