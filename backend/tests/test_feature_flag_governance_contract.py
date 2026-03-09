import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_feature_flag_governance_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_feature_flag_governance_contract", SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load module from {SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class FeatureFlagGovernanceContractTests(unittest.TestCase):
    def test_feature_flag_governance_contract_passes_repository_state(self) -> None:
        violations = _MODULE.collect_feature_flag_governance_violations()
        self.assertEqual(violations, [])

    def test_feature_flag_governance_contract_detects_missing_runtime_entry(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["entries"] = [entry for entry in payload["entries"] if entry.get("flag") != "websocket_realtime_enabled"]
        violations = _MODULE.collect_feature_flag_governance_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_runtime_flag_entry" for v in violations))

    def test_feature_flag_governance_contract_detects_mapping_mismatch(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        for entry in payload["entries"]:
            if entry.get("flag") == "repair_flow_v1":
                entry["kill_switch"] = "disable_webpush"
                break
        violations = _MODULE.collect_feature_flag_governance_violations(payload=payload)
        self.assertTrue(any(v.reason == "kill_switch_mapping_mismatch" for v in violations))


if __name__ == "__main__":
    unittest.main()
