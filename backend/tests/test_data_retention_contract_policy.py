import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_data_retention_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_data_retention_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class DataRetentionContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_data_retention_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_audit_retention_days_mismatch(self) -> None:
        payload = json.loads(_MODULE.RETENTION_POLICY_PATH.read_text(encoding="utf-8"))
        for item in payload["policies"]:
            if item.get("data_class") == "audit_events":
                item["retention_days_default"] = 30
                break

        violations = _MODULE.collect_data_retention_contract_violations(
            retention_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "audit_retention_days_mismatch" for v in violations))

    def test_policy_rejects_missing_required_erase_data_class(self) -> None:
        payload = json.loads(_MODULE.RETENTION_POLICY_PATH.read_text(encoding="utf-8"))
        payload["policies"] = [
            item for item in payload["policies"] if item.get("data_class") != "journals"
        ]

        violations = _MODULE.collect_data_retention_contract_violations(
            retention_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "missing_required_data_class" for v in violations))

    def test_policy_rejects_erase_data_class_with_wrong_delete_mode(self) -> None:
        payload = json.loads(_MODULE.RETENTION_POLICY_PATH.read_text(encoding="utf-8"))
        for item in payload["policies"]:
            if item.get("data_class") == "card_sessions":
                item["delete_mode"] = "ttl_expiry"
                item["trigger"] = "time_based"
                item["retention_days_default"] = 10
                item["retention_days_env"] = "CARD_SESSION_RETENTION_DAYS"
                break

        violations = _MODULE.collect_data_retention_contract_violations(
            retention_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "erase_data_class_invalid_delete_mode" for v in violations))


if __name__ == "__main__":
    unittest.main()
