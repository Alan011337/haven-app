import importlib.util
import json
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

VALIDATOR_PATH = BACKEND_ROOT / "scripts" / "validate_security_evidence.py"
_SPEC = importlib.util.spec_from_file_location("validate_security_evidence", VALIDATOR_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"Unable to load validator module from {VALIDATOR_PATH}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

REQUIRED_P0_DRILL_CHECKS = _MODULE.REQUIRED_P0_DRILL_CHECKS
REQUIRED_DATA_RIGHTS_DRILL_CHECKS = _MODULE.REQUIRED_DATA_RIGHTS_DRILL_CHECKS
REQUIRED_BILLING_DRILL_CHECKS = _MODULE.REQUIRED_BILLING_DRILL_CHECKS
EVIDENCE_SCHEMA_VERSION = _MODULE.EVIDENCE_SCHEMA_VERSION
P0_DRILL_ARTIFACT_KIND = _MODULE.P0_DRILL_ARTIFACT_KIND
P0_DRILL_GENERATED_BY = _MODULE.P0_DRILL_GENERATED_BY
DATA_RIGHTS_FIRE_DRILL_KIND = _MODULE.DATA_RIGHTS_FIRE_DRILL_KIND
BILLING_FIRE_DRILL_KIND = _MODULE.BILLING_FIRE_DRILL_KIND
BILLING_RECON_ARTIFACT_KIND = _MODULE.BILLING_RECON_ARTIFACT_KIND
BILLING_RECON_GENERATED_BY = _MODULE.BILLING_RECON_GENERATED_BY
AUDIT_RETENTION_ARTIFACT_KIND = _MODULE.AUDIT_RETENTION_ARTIFACT_KIND
AUDIT_RETENTION_GENERATED_BY = _MODULE.AUDIT_RETENTION_GENERATED_BY
BILLING_CONSOLE_DRIFT_ARTIFACT_KIND = _MODULE.BILLING_CONSOLE_DRIFT_ARTIFACT_KIND
BILLING_CONSOLE_DRIFT_GENERATED_BY = _MODULE.BILLING_CONSOLE_DRIFT_GENERATED_BY
BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS = _MODULE.BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS
DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND = _MODULE.DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND
DATA_SOFT_DELETE_PURGE_GENERATED_BY = _MODULE.DATA_SOFT_DELETE_PURGE_GENERATED_BY
KEY_ROTATION_DRILL_ARTIFACT_KIND = _MODULE.KEY_ROTATION_DRILL_ARTIFACT_KIND
KEY_ROTATION_DRILL_GENERATED_BY = _MODULE.KEY_ROTATION_DRILL_GENERATED_BY
KEY_ROTATION_DRILL_REQUIRED_CHECKS = _MODULE.KEY_ROTATION_DRILL_REQUIRED_CHECKS
DATA_RESTORE_DRILL_ARTIFACT_KIND = _MODULE.DATA_RESTORE_DRILL_ARTIFACT_KIND
DATA_RESTORE_DRILL_GENERATED_BY = _MODULE.DATA_RESTORE_DRILL_GENERATED_BY
DATA_RESTORE_DRILL_REQUIRED_CHECKS = _MODULE.DATA_RESTORE_DRILL_REQUIRED_CHECKS
BACKUP_RESTORE_DRILL_ARTIFACT_KIND = _MODULE.BACKUP_RESTORE_DRILL_ARTIFACT_KIND
BACKUP_RESTORE_DRILL_GENERATED_BY = _MODULE.BACKUP_RESTORE_DRILL_GENERATED_BY
BACKUP_RESTORE_DRILL_REQUIRED_CHECKS = _MODULE.BACKUP_RESTORE_DRILL_REQUIRED_CHECKS
CHAOS_DRILL_ARTIFACT_KIND = _MODULE.CHAOS_DRILL_ARTIFACT_KIND
CHAOS_DRILL_GENERATED_BY = _MODULE.CHAOS_DRILL_GENERATED_BY
CHAOS_DRILL_REQUIRED_DRILLS = _MODULE.CHAOS_DRILL_REQUIRED_DRILLS
CHAOS_DRILL_REQUIRED_CHECKS = _MODULE.CHAOS_DRILL_REQUIRED_CHECKS
CONTRACT_MODE_STRICT = _MODULE.CONTRACT_MODE_STRICT
CONTRACT_MODE_COMPAT = _MODULE.CONTRACT_MODE_COMPAT
validate_billing_reconciliation_payload = _MODULE.validate_billing_reconciliation_payload
validate_audit_retention_payload = _MODULE.validate_audit_retention_payload
validate_billing_console_drift_payload = _MODULE.validate_billing_console_drift_payload
validate_data_soft_delete_purge_payload = _MODULE.validate_data_soft_delete_purge_payload
validate_key_rotation_drill_payload = _MODULE.validate_key_rotation_drill_payload
validate_data_restore_drill_payload = _MODULE.validate_data_restore_drill_payload
validate_backup_restore_drill_payload = _MODULE.validate_backup_restore_drill_payload
validate_chaos_drill_payload = _MODULE.validate_chaos_drill_payload
validate_p0_drill_payload = _MODULE.validate_p0_drill_payload
validate_data_rights_fire_drill_payload = _MODULE.validate_data_rights_fire_drill_payload
validate_billing_fire_drill_payload = _MODULE.validate_billing_fire_drill_payload
validate_evidence_freshness = _MODULE.validate_evidence_freshness


class SecurityEvidenceValidationTests(unittest.TestCase):
    def test_validate_p0_drill_payload_accepts_valid_payload(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [
                {"name": name, "ok": True, "detail": "ok"}
                for name in checks
            ],
        }
        errors = validate_p0_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_p0_drill_payload_rejects_missing_required_checks(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "required_checks": checks,
            "checks_total": len(checks) - 1,
            "checks_passed": len(checks) - 1,
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks[:-1]],
        }
        errors = validate_p0_drill_payload(payload)
        self.assertTrue(any("Missing required drill checks" in item for item in errors))

    def test_validate_p0_drill_payload_rejects_all_passed_mismatch(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks) - 1,
            "checks_failed": 1,
            "all_passed": True,
            "results": [
                {
                    "name": checks[0],
                    "ok": False,
                    "detail": "failed",
                },
                *[
                    {"name": name, "ok": True, "detail": "ok"}
                    for name in checks[1:]
                ],
            ],
        }
        errors = validate_p0_drill_payload(payload)
        self.assertTrue(any("`all_passed` mismatch" in item for item in errors))

    def test_validate_p0_drill_payload_rejects_schema_version_mismatch(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)
        payload = {
            "schema_version": "0.0.0",
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_p0_drill_payload(payload)
        self.assertTrue(any("`schema_version` must be" in item for item in errors))

    def test_validate_data_rights_fire_drill_accepts_valid_subset_checks(self) -> None:
        checks = sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_RIGHTS_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [
                {"name": name, "ok": True, "detail": "ok"}
                for name in checks
            ],
        }
        errors = validate_data_rights_fire_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_data_rights_fire_drill_rejects_missing_required_check(self) -> None:
        checks = sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_RIGHTS_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [
                {"name": name, "ok": True, "detail": "ok"}
                for name in checks[:-1]
            ],
        }
        errors = validate_data_rights_fire_drill_payload(payload)
        self.assertTrue(any("Missing required data-rights drill checks" in item for item in errors))

    def test_validate_data_rights_fire_drill_rejects_failed_required_check(self) -> None:
        checks = sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_RIGHTS_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": False,
            "results": [
                {"name": checks[0], "ok": False, "detail": "failed"},
                {"name": checks[1], "ok": True, "detail": "ok"},
                {"name": checks[2], "ok": True, "detail": "ok"},
            ],
        }
        errors = validate_data_rights_fire_drill_payload(payload)
        self.assertTrue(any("must pass (`ok=true`)" in item for item in errors))

    def test_validate_data_rights_fire_drill_strict_accepts_legacy_p0_artifact_kind(self) -> None:
        checks = sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_data_rights_fire_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_billing_fire_drill_accepts_valid_subset_checks(self) -> None:
        checks = sorted(REQUIRED_BILLING_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_billing_fire_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_billing_fire_drill_rejects_missing_required_check(self) -> None:
        checks = sorted(REQUIRED_BILLING_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks[:-1]],
        }
        errors = validate_billing_fire_drill_payload(payload)
        self.assertTrue(any("Missing required billing drill checks" in item for item in errors))

    def test_validate_billing_fire_drill_rejects_failed_required_check(self) -> None:
        checks = sorted(REQUIRED_BILLING_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_FIRE_DRILL_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": False,
            "results": [
                {"name": checks[0], "ok": False, "detail": "failed"},
                *[
                    {"name": name, "ok": True, "detail": "ok"}
                    for name in checks[1:]
                ],
            ],
        }
        errors = validate_billing_fire_drill_payload(payload)
        self.assertTrue(any("Billing drill check" in item and "must pass (`ok=true`)" in item for item in errors))

    def test_validate_billing_fire_drill_strict_accepts_legacy_p0_artifact_kind(self) -> None:
        checks = sorted(REQUIRED_BILLING_DRILL_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": P0_DRILL_ARTIFACT_KIND,
            "generated_by": P0_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_billing_fire_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_billing_payload_accepts_valid_payload(self) -> None:
        user_id = "d73f6f13-1a0d-4c4b-b103-3d443f8ad4e0"
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_RECON_ARTIFACT_KIND,
            "generated_by": BILLING_RECON_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "total_users": 1,
            "healthy_users": 1,
            "unhealthy_users": 0,
            "results": [
                {
                    "user_id": user_id,
                    "command_count": 1,
                    "command_ledger_count": 1,
                    "missing_command_ledger_count": 0,
                    "missing_command_ids": [],
                    "entitlement_state": "ACTIVE",
                    "entitlement_plan": "PREMIUM",
                    "healthy": True,
                }
            ],
        }
        errors = validate_billing_reconciliation_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_billing_payload_rejects_count_inconsistency(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_RECON_ARTIFACT_KIND,
            "generated_by": BILLING_RECON_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "total_users": 2,
            "healthy_users": 2,
            "unhealthy_users": 0,
            "results": [],
        }
        errors = validate_billing_reconciliation_payload(payload)
        self.assertTrue(any("`total_users` mismatch" in item for item in errors))

    def test_validate_billing_payload_rejects_invalid_user_id(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_RECON_ARTIFACT_KIND,
            "generated_by": BILLING_RECON_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "total_users": 1,
            "healthy_users": 1,
            "unhealthy_users": 0,
            "results": [
                {
                    "user_id": "not-a-uuid",
                    "command_count": 0,
                    "command_ledger_count": 0,
                    "missing_command_ledger_count": 0,
                    "missing_command_ids": [],
                    "entitlement_state": None,
                    "entitlement_plan": None,
                    "healthy": True,
                }
            ],
        }
        errors = validate_billing_reconciliation_payload(payload)
        self.assertTrue(any("not a valid UUID" in item for item in errors))

    def test_validate_billing_payload_rejects_artifact_kind_mismatch(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": "wrong-kind",
            "generated_by": BILLING_RECON_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "total_users": 0,
            "healthy_users": 0,
            "unhealthy_users": 0,
            "results": [],
        }
        errors = validate_billing_reconciliation_payload(payload)
        self.assertTrue(any("`artifact_kind` must be" in item for item in errors))

    def test_validate_p0_drill_payload_compat_accepts_legacy_shape(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)[:2]
        payload = {
            "generated_at": "2026-02-16T14:00:00+00:00",
            "all_passed": True,
            "results": [
                {"name": name, "ok": True, "detail": "ok"}
                for name in checks
            ],
        }
        errors = validate_p0_drill_payload(payload, contract_mode=CONTRACT_MODE_COMPAT)
        self.assertEqual(errors, [])

    def test_validate_p0_drill_payload_compat_rejects_required_checks_mismatch(self) -> None:
        checks = sorted(REQUIRED_P0_DRILL_CHECKS)
        payload = {
            "generated_at": "2026-02-16T14:00:00+00:00",
            "required_checks": [checks[0]],
            "all_passed": True,
            "results": [
                {"name": checks[1], "ok": True, "detail": "ok"},
            ],
        }
        errors = validate_p0_drill_payload(payload, contract_mode=CONTRACT_MODE_COMPAT)
        self.assertTrue(
            any(
                "must match sorted unique `results[].name` in compat validation" in item
                for item in errors
            )
        )

    def test_validate_billing_payload_compat_accepts_legacy_shape(self) -> None:
        user_id = "d73f6f13-1a0d-4c4b-b103-3d443f8ad4e0"
        payload = {
            "generated_at": "2026-02-16T14:00:00+00:00",
            "total_users": 1,
            "healthy_users": 1,
            "unhealthy_users": 0,
            "results": [
                {
                    "user_id": user_id,
                    "command_count": 1,
                    "command_ledger_count": 1,
                    "missing_command_ledger_count": 0,
                    "missing_command_ids": [],
                    "entitlement_state": "ACTIVE",
                    "entitlement_plan": "PREMIUM",
                    "healthy": True,
                }
            ],
        }
        errors = validate_billing_reconciliation_payload(
            payload,
            contract_mode=CONTRACT_MODE_COMPAT,
        )
        self.assertEqual(errors, [])

    def test_validate_audit_retention_payload_accepts_valid_payload(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": AUDIT_RETENTION_ARTIFACT_KIND,
            "generated_by": AUDIT_RETENTION_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "retention_days": 365,
            "before_count": 10,
            "deleted_count": 3,
            "after_count": 7,
            "healthy": True,
        }
        errors = validate_audit_retention_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_audit_retention_payload_rejects_count_mismatch(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": AUDIT_RETENTION_ARTIFACT_KIND,
            "generated_by": AUDIT_RETENTION_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "retention_days": 365,
            "before_count": 10,
            "deleted_count": 4,
            "after_count": 8,
            "healthy": True,
        }
        errors = validate_audit_retention_payload(payload)
        self.assertTrue(any("`after_count` mismatch" in item for item in errors))

    def test_validate_billing_console_drift_payload_accepts_valid_payload(self) -> None:
        checks = list(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_CONSOLE_DRIFT_ARTIFACT_KIND,
            "generated_by": BILLING_CONSOLE_DRIFT_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T05:00:00+00:00",
            "dry_run": True,
            "provider": "stripe",
            "runbook_path": "docs/billing/console-drift-monitor.md",
            "policy_path": "docs/security/billing-console-drift-policy.json",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "runtime": {
                "webhook_tolerance_seconds": 300,
                "webhook_async_mode": False,
            },
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_billing_console_drift_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_billing_console_drift_payload_rejects_missing_required_check(self) -> None:
        checks = list(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BILLING_CONSOLE_DRIFT_ARTIFACT_KIND,
            "generated_by": BILLING_CONSOLE_DRIFT_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T05:00:00+00:00",
            "dry_run": True,
            "provider": "stripe",
            "runbook_path": "docs/billing/console-drift-monitor.md",
            "policy_path": "docs/security/billing-console-drift-policy.json",
            "required_checks": checks,
            "checks_total": len(checks) - 1,
            "checks_passed": len(checks) - 1,
            "checks_failed": 0,
            "all_passed": True,
            "runtime": {
                "webhook_tolerance_seconds": 300,
                "webhook_async_mode": False,
            },
            "results": [
                {"name": name, "ok": True, "detail": "ok"}
                for name in checks[:-1]
            ],
        }
        errors = validate_billing_console_drift_payload(payload)
        self.assertTrue(any("must cover exactly" in item for item in errors))

    def test_validate_data_soft_delete_purge_payload_accepts_valid_payload(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND,
            "generated_by": DATA_SOFT_DELETE_PURGE_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "mode": "dry_run",
            "soft_delete_enabled": False,
            "retention_days": 90,
            "cutoff_iso": "2026-02-01T00:00:00+00:00",
            "candidate_counts": {
                "analyses": 0,
                "journals": 0,
                "card_responses": 0,
                "card_sessions": 0,
                "notification_events": 0,
                "users": 0,
            },
            "purged_counts": {
                "analyses": 0,
                "journals": 0,
                "card_responses": 0,
                "card_sessions": 0,
                "notification_events": 0,
                "users": 0,
            },
            "total_candidates": 0,
            "total_purged": 0,
            "healthy": True,
        }
        errors = validate_data_soft_delete_purge_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_data_soft_delete_purge_payload_rejects_dry_run_with_purged_rows(self) -> None:
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND,
            "generated_by": DATA_SOFT_DELETE_PURGE_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-16T14:00:00+00:00",
            "mode": "dry_run",
            "soft_delete_enabled": False,
            "retention_days": 90,
            "cutoff_iso": "2026-02-01T00:00:00+00:00",
            "candidate_counts": {
                "analyses": 1,
                "journals": 0,
                "card_responses": 0,
                "card_sessions": 0,
                "notification_events": 0,
                "users": 0,
            },
            "purged_counts": {
                "analyses": 1,
                "journals": 0,
                "card_responses": 0,
                "card_sessions": 0,
                "notification_events": 0,
                "users": 0,
            },
            "total_candidates": 1,
            "total_purged": 1,
            "healthy": True,
        }
        errors = validate_data_soft_delete_purge_payload(payload)
        self.assertTrue(any("must be 0 when mode=dry_run" in item for item in errors))

    def test_validate_key_rotation_drill_payload_accepts_valid_payload(self) -> None:
        checks = list(KEY_ROTATION_DRILL_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": KEY_ROTATION_DRILL_ARTIFACT_KIND,
            "generated_by": KEY_ROTATION_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "kms_provider": "mock-kms",
            "runbook_path": "docs/security/keys.md",
            "policy_path": "docs/security/secrets-key-management-policy.json",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_key_rotation_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_key_rotation_drill_payload_rejects_invalid_dry_run(self) -> None:
        checks = list(KEY_ROTATION_DRILL_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": KEY_ROTATION_DRILL_ARTIFACT_KIND,
            "generated_by": KEY_ROTATION_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": False,
            "kms_provider": "mock-kms",
            "runbook_path": "docs/security/keys.md",
            "policy_path": "docs/security/secrets-key-management-policy.json",
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_key_rotation_drill_payload(payload)
        self.assertTrue(any("`dry_run` must be true" in item for item in errors))

    def test_validate_data_restore_drill_payload_accepts_valid_payload(self) -> None:
        checks = list(DATA_RESTORE_DRILL_REQUIRED_CHECKS)
        source_path = _MODULE._resolve_latest_evidence_path("data-soft-delete-purge")  # noqa: SLF001
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        source_generated_at = source_payload.get("generated_at")
        if not isinstance(source_generated_at, str):
            source_generated_at = "2026-02-23T00:00:00+00:00"
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_RESTORE_DRILL_ARTIFACT_KIND,
            "generated_by": DATA_RESTORE_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/security/data-restore-rehearsal.md",
            "policy_path": "docs/security/data-deletion-lifecycle-policy.json",
            "source_evidence_kind": DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND,
            "source_evidence_path": str(source_path.relative_to(_MODULE.REPO_ROOT)),
            "source_evidence_generated_at": source_generated_at,
            "source_evidence_max_age_days": 35,
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_data_restore_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_data_restore_drill_payload_rejects_invalid_source_kind(self) -> None:
        checks = list(DATA_RESTORE_DRILL_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": DATA_RESTORE_DRILL_ARTIFACT_KIND,
            "generated_by": DATA_RESTORE_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/security/data-restore-rehearsal.md",
            "policy_path": "docs/security/data-deletion-lifecycle-policy.json",
            "source_evidence_kind": "wrong-kind",
            "source_evidence_path": "docs/security/data-soft-delete-purge-audit.md",
            "source_evidence_generated_at": "2026-02-23T00:00:00+00:00",
            "source_evidence_max_age_days": 35,
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_data_restore_drill_payload(payload)
        self.assertTrue(any("`source_evidence_kind` must be" in item for item in errors))

    def test_validate_backup_restore_drill_payload_accepts_valid_payload(self) -> None:
        checks = list(BACKUP_RESTORE_DRILL_REQUIRED_CHECKS)
        source_path = _MODULE._resolve_latest_evidence_path("data-restore-drill")  # noqa: SLF001
        source_payload = json.loads(source_path.read_text(encoding="utf-8"))
        source_generated_at = source_payload.get("generated_at")
        if not isinstance(source_generated_at, str):
            source_generated_at = "2026-02-23T00:00:00+00:00"
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BACKUP_RESTORE_DRILL_ARTIFACT_KIND,
            "generated_by": BACKUP_RESTORE_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/ops/backup-restore-runbook.md",
            "policy_path": "docs/ops/backup-policy.json",
            "source_evidence_kind": DATA_RESTORE_DRILL_ARTIFACT_KIND,
            "source_evidence_path": str(source_path.relative_to(_MODULE.REPO_ROOT)),
            "source_evidence_generated_at": source_generated_at,
            "source_evidence_max_age_days": 120,
            "backup_encryption_required": True,
            "backup_retention_days": 35,
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_backup_restore_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_backup_restore_drill_payload_rejects_invalid_source_kind(self) -> None:
        checks = list(BACKUP_RESTORE_DRILL_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": BACKUP_RESTORE_DRILL_ARTIFACT_KIND,
            "generated_by": BACKUP_RESTORE_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/ops/backup-restore-runbook.md",
            "policy_path": "docs/ops/backup-policy.json",
            "source_evidence_kind": "wrong-kind",
            "source_evidence_path": "docs/security/data-restore-rehearsal.md",
            "source_evidence_generated_at": "2026-02-23T00:00:00+00:00",
            "source_evidence_max_age_days": 120,
            "backup_encryption_required": True,
            "backup_retention_days": 35,
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_backup_restore_drill_payload(payload)
        self.assertTrue(any("`source_evidence_kind` must be" in item for item in errors))

    def test_validate_chaos_drill_payload_accepts_valid_payload(self) -> None:
        checks = list(CHAOS_DRILL_REQUIRED_CHECKS)
        drills = list(CHAOS_DRILL_REQUIRED_DRILLS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": CHAOS_DRILL_ARTIFACT_KIND,
            "generated_by": CHAOS_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/ops/chaos-drill-spec.md",
            "incident_playbook_path": "docs/ops/incident-response-playbook.md",
            "report_template_path": "docs/ops/chaos-drill-report-template.md",
            "workflow_path": ".github/workflows/chaos-drill.yml",
            "required_drills": drills,
            "executed_drills": drills,
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_chaos_drill_payload(payload)
        self.assertEqual(errors, [])

    def test_validate_chaos_drill_payload_rejects_invalid_required_drills(self) -> None:
        checks = list(CHAOS_DRILL_REQUIRED_CHECKS)
        payload = {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "artifact_kind": CHAOS_DRILL_ARTIFACT_KIND,
            "generated_by": CHAOS_DRILL_GENERATED_BY,
            "contract_mode": CONTRACT_MODE_STRICT,
            "generated_at": "2026-02-23T00:00:00+00:00",
            "dry_run": True,
            "runbook_path": "docs/ops/chaos-drill-spec.md",
            "incident_playbook_path": "docs/ops/incident-response-playbook.md",
            "report_template_path": "docs/ops/chaos-drill-report-template.md",
            "workflow_path": ".github/workflows/chaos-drill.yml",
            "required_drills": ["ws_storm"],
            "executed_drills": ["ws_storm"],
            "required_checks": checks,
            "checks_total": len(checks),
            "checks_passed": len(checks),
            "checks_failed": 0,
            "all_passed": True,
            "results": [{"name": name, "ok": True, "detail": "ok"} for name in checks],
        }
        errors = validate_chaos_drill_payload(payload)
        self.assertTrue(any("`required_drills` must equal" in item for item in errors))

    def test_validate_evidence_freshness_accepts_recent_payload(self) -> None:
        now = datetime(2026, 2, 17, 4, 40, tzinfo=timezone.utc)
        payload = {
            "generated_at": (now - timedelta(days=3)).isoformat(),
        }
        errors = validate_evidence_freshness(payload, max_age_days=35, now_utc=now)
        self.assertEqual(errors, [])

    def test_validate_evidence_freshness_rejects_stale_payload(self) -> None:
        now = datetime(2026, 2, 17, 4, 40, tzinfo=timezone.utc)
        payload = {
            "generated_at": (now - timedelta(days=40)).isoformat(),
        }
        errors = validate_evidence_freshness(payload, max_age_days=35, now_utc=now)
        self.assertTrue(any("evidence is stale" in item for item in errors))

    def test_validate_evidence_freshness_rejects_future_timestamp(self) -> None:
        now = datetime(2026, 2, 17, 4, 40, tzinfo=timezone.utc)
        payload = {
            "generated_at": (now + timedelta(minutes=10)).isoformat(),
        }
        errors = validate_evidence_freshness(payload, max_age_days=35, now_utc=now)
        self.assertTrue(any("in the future" in item for item in errors))


if __name__ == "__main__":
    unittest.main()
