import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_growth_kill_switch_coverage_contract.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_growth_kill_switch_coverage_contract",
    SCRIPT_PATH,
)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class GrowthKillSwitchCoverageContractTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_growth_kill_switch_coverage_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_required_cuj_flag_entry(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["entries"] = [item for item in payload["entries"] if item.get("flag") != "growth_pricing_experiment_enabled"]
        violations = _MODULE.collect_growth_kill_switch_coverage_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_required_cuj_flag" for v in violations))

    def test_policy_rejects_missing_runtime_mapping(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        fake_feature_flags_module = type(
            "FakeFeatureFlagsModule",
            (),
            {
                "DEFAULT_FEATURE_FLAGS": {"growth_referral_enabled": True},
                "DEFAULT_KILL_SWITCHES": {"disable_referral_funnel": False},
                "KILL_SWITCH_TO_FLAG": {"disable_referral_funnel": "growth_referral_enabled"},
            },
        )
        violations = _MODULE.collect_growth_kill_switch_coverage_violations(
            payload=payload,
            feature_flags_module=fake_feature_flags_module,
        )
        self.assertTrue(any(v.reason == "flag_missing_in_runtime" for v in violations))
        self.assertTrue(any(v.reason == "kill_switch_missing_in_runtime" for v in violations))


if __name__ == "__main__":
    unittest.main()
