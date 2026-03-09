import importlib.util
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

POLICY_SCRIPT_PATH = BACKEND_ROOT / "scripts" / "check_data_rights_contract.py"
_SPEC = importlib.util.spec_from_file_location("check_data_rights_contract", POLICY_SCRIPT_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load policy module from {POLICY_SCRIPT_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE
_SPEC.loader.exec_module(_MODULE)


class DataRightsContractPolicyTests(unittest.TestCase):
    def test_policy_passes_for_current_repository_state(self) -> None:
        violations = _MODULE.collect_data_rights_contract_violations()
        self.assertEqual(violations, [])

    def test_policy_rejects_export_section_mismatch(self) -> None:
        export_spec_payload = {
            "artifact_kind": _MODULE.EXPORT_SPEC_ARTIFACT_KIND,
            "schema_version": _MODULE.EXPORT_SPEC_SCHEMA_VERSION,
            "endpoint": _MODULE.EXPORT_ENDPOINT,
            "export_version": _MODULE.EXPECTED_EXPORT_VERSION,
            "expires_after_days_default": 7,
            "sections": [
                {"name": "user", "required": True, "owner_scope": "current_user"},
                {"name": "journals", "required": True, "owner_scope": "current_user"},
            ],
        }
        deletion_graph_payload = {
            "artifact_kind": _MODULE.DELETION_GRAPH_ARTIFACT_KIND,
            "schema_version": _MODULE.DELETION_GRAPH_SCHEMA_VERSION,
            "endpoint": _MODULE.ERASE_ENDPOINT,
            "deleted_count_keys": list(_MODULE.DATA_ERASE_COUNT_KEYS),
            "resources": [
                {"name": "user", "delete_mode": "hard_delete", "owner_key": "user.id"},
                {
                    "name": "analysis",
                    "delete_mode": "hard_delete",
                    "owner_key": "analysis.journal_id",
                },
                {
                    "name": "journal",
                    "delete_mode": "hard_delete",
                    "owner_key": "journal.user_id",
                },
                {
                    "name": "card_response",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_response.user_id",
                },
                {
                    "name": "card_session",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_session.creator_id|partner_id",
                },
                {
                    "name": "notification_event",
                    "delete_mode": "hard_delete",
                    "owner_key": "sender_or_receiver",
                },
            ],
            "edges": [
                {"from": "user", "to": "journal", "reason": "ownership"},
                {"from": "journal", "to": "analysis", "reason": "journal_id"},
            ],
        }

        violations = _MODULE.collect_data_rights_contract_violations(
            export_spec_payload=export_spec_payload,
            deletion_graph_payload=deletion_graph_payload,
        )

        self.assertTrue(any(v.reason == "section_order_mismatch" for v in violations))

    def test_policy_rejects_export_expiry_mismatch(self) -> None:
        export_spec_payload = {
            "artifact_kind": _MODULE.EXPORT_SPEC_ARTIFACT_KIND,
            "schema_version": _MODULE.EXPORT_SPEC_SCHEMA_VERSION,
            "endpoint": _MODULE.EXPORT_ENDPOINT,
            "export_version": _MODULE.EXPECTED_EXPORT_VERSION,
            "expires_after_days_default": 14,
            "sections": [
                {"name": name, "required": True, "owner_scope": "current_user"}
                for name in _MODULE.DATA_EXPORT_SECTION_KEYS
            ],
        }
        deletion_graph_payload = {
            "artifact_kind": _MODULE.DELETION_GRAPH_ARTIFACT_KIND,
            "schema_version": _MODULE.DELETION_GRAPH_SCHEMA_VERSION,
            "endpoint": _MODULE.ERASE_ENDPOINT,
            "deleted_count_keys": list(_MODULE.DATA_ERASE_COUNT_KEYS),
            "resources": [
                {"name": "user", "delete_mode": "hard_delete", "owner_key": "user.id"},
                {
                    "name": "analysis",
                    "delete_mode": "hard_delete",
                    "owner_key": "analysis.journal_id",
                },
                {
                    "name": "journal",
                    "delete_mode": "hard_delete",
                    "owner_key": "journal.user_id",
                },
                {
                    "name": "card_response",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_response.user_id",
                },
                {
                    "name": "card_session",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_session.creator_id|partner_id",
                },
                {
                    "name": "notification_event",
                    "delete_mode": "hard_delete",
                    "owner_key": "sender_or_receiver",
                },
            ],
            "edges": [
                {"from": "user", "to": "journal", "reason": "ownership"},
                {"from": "journal", "to": "analysis", "reason": "journal_id"},
            ],
        }

        violations = _MODULE.collect_data_rights_contract_violations(
            export_spec_payload=export_spec_payload,
            deletion_graph_payload=deletion_graph_payload,
            export_expiry_days=7,
        )

        self.assertTrue(any(v.reason == "expiry_days_mismatch" for v in violations))

    def test_policy_rejects_deletion_key_mismatch(self) -> None:
        export_spec_payload = {
            "artifact_kind": _MODULE.EXPORT_SPEC_ARTIFACT_KIND,
            "schema_version": _MODULE.EXPORT_SPEC_SCHEMA_VERSION,
            "endpoint": _MODULE.EXPORT_ENDPOINT,
            "export_version": _MODULE.EXPECTED_EXPORT_VERSION,
            "expires_after_days_default": 7,
            "sections": [
                {"name": name, "required": True, "owner_scope": "current_user"}
                for name in _MODULE.DATA_EXPORT_SECTION_KEYS
            ],
        }
        deletion_graph_payload = {
            "artifact_kind": _MODULE.DELETION_GRAPH_ARTIFACT_KIND,
            "schema_version": _MODULE.DELETION_GRAPH_SCHEMA_VERSION,
            "endpoint": _MODULE.ERASE_ENDPOINT,
            "deleted_count_keys": ["journals", "users"],
            "resources": [
                {"name": "user", "delete_mode": "hard_delete", "owner_key": "user.id"},
                {
                    "name": "analysis",
                    "delete_mode": "hard_delete",
                    "owner_key": "analysis.journal_id",
                },
                {
                    "name": "journal",
                    "delete_mode": "hard_delete",
                    "owner_key": "journal.user_id",
                },
                {
                    "name": "card_response",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_response.user_id",
                },
                {
                    "name": "card_session",
                    "delete_mode": "hard_delete",
                    "owner_key": "card_session.creator_id|partner_id",
                },
                {
                    "name": "notification_event",
                    "delete_mode": "hard_delete",
                    "owner_key": "sender_or_receiver",
                },
            ],
            "edges": [
                {"from": "user", "to": "journal", "reason": "ownership"},
                {"from": "journal", "to": "analysis", "reason": "journal_id"},
            ],
        }

        violations = _MODULE.collect_data_rights_contract_violations(
            export_spec_payload=export_spec_payload,
            deletion_graph_payload=deletion_graph_payload,
        )

        self.assertTrue(any(v.reason == "deleted_count_keys_mismatch" for v in violations))


if __name__ == "__main__":
    unittest.main()
