import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_data_classification_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_data_classification_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class DataClassificationContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_data_classification_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_sensitivity_mapping(self) -> None:
        payload = json.loads(_MODULE.CLASSIFICATION_POLICY_PATH.read_text(encoding="utf-8"))
        payload["sensitivity_mapping"].pop("account_sensitive", None)

        violations = _MODULE.collect_data_classification_contract_violations(
            classification_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "missing_sensitivity_mapping" for v in violations))

    def test_policy_rejects_unexpected_billing_mapping(self) -> None:
        payload = json.loads(_MODULE.CLASSIFICATION_POLICY_PATH.read_text(encoding="utf-8"))
        payload["sensitivity_mapping"]["billing_sensitive"] = "pii_sensitive"

        violations = _MODULE.collect_data_classification_contract_violations(
            classification_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "unexpected_default_mapping" for v in violations))

    def test_policy_rejects_missing_handling_rule_for_taxonomy(self) -> None:
        payload = json.loads(_MODULE.CLASSIFICATION_POLICY_PATH.read_text(encoding="utf-8"))
        payload["handling_rules"].pop("intimate_sensitive", None)

        violations = _MODULE.collect_data_classification_contract_violations(
            classification_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "missing_handling_rule" for v in violations))


if __name__ == "__main__":
    unittest.main()
