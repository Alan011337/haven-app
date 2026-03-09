import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_store_compliance_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_store_compliance_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class StoreComplianceContractTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_store_compliance_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_platform(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["platforms"].pop("google_play", None)
        violations = _MODULE.collect_store_compliance_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_platform_entry" for v in violations))

    def test_policy_rejects_invalid_age_rating(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["platforms"]["ios_app_store"]["age_rating"] = "12+"
        violations = _MODULE.collect_store_compliance_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "invalid_age_rating" for v in violations))

    def test_policy_rejects_missing_entitlement_parity_reference(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["references"].pop("entitlement_parity_test", None)
        violations = _MODULE.collect_store_compliance_contract_violations(payload=payload)
        self.assertTrue(any(v.reason == "missing_reference_key" for v in violations))


if __name__ == "__main__":
    unittest.main()
