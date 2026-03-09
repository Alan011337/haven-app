import importlib.util
import json
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_data_deletion_lifecycle_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_data_deletion_lifecycle_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class DataDeletionLifecycleContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_missing_erase_resource(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["resources"] = [
            item for item in payload["resources"] if item.get("data_class") != "journals"
        ]

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "missing_erase_resource" for v in violations))

    def test_policy_rejects_soft_delete_disabled_with_non_hard_delete(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        for item in payload["resources"]:
            if item.get("data_class") == "card_sessions":
                item["current_delete_mode"] = "soft_delete_then_purge"
                break

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
        )
        self.assertTrue(
            any(v.reason == "soft_delete_disabled_but_non_hard_delete_resource" for v in violations)
        )

    def test_policy_rejects_missing_required_audit_action(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["required_audit_actions"] = ["USER_DATA_ERASE"]

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "required_audit_actions_mismatch" for v in violations))

    def test_policy_rejects_runtime_soft_delete_enabled_mismatch(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["phase_gate"]["soft_delete_enabled"] = False

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
            soft_delete_enabled_setting=True,
        )
        self.assertTrue(any(v.reason == "soft_delete_enabled_setting_mismatch" for v in violations))

    def test_policy_rejects_missing_deleted_at_schema_hook(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
            model_deleted_at_support={
                "analyses": True,
                "journals": True,
                "card_responses": True,
                "card_sessions": False,
                "notification_events": True,
                "users": True,
            },
        )
        self.assertTrue(any(v.reason == "missing_deleted_at_schema_hook" for v in violations))

    def test_policy_rejects_runtime_settings_mismatch(self) -> None:
        payload = json.loads(_MODULE.POLICY_PATH.read_text(encoding="utf-8"))
        payload["runtime_settings"]["soft_delete_enabled_env"] = "WRONG_ENV"

        violations = _MODULE.collect_data_deletion_lifecycle_contract_violations(
            lifecycle_policy_payload=payload,
        )
        self.assertTrue(any(v.reason == "runtime_settings_mismatch" for v in violations))


if __name__ == "__main__":
    unittest.main()
