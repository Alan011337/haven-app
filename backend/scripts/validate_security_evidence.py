#!/usr/bin/env python3
"""Validate security evidence JSON artifacts with deterministic schema checks."""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.security_evidence_utils import (
        is_non_negative_int as _is_non_negative_int,
    )
    from scripts.security_evidence_utils import (
        parse_iso8601 as _parse_iso8601,
    )
    from scripts.security_evidence_utils import (
        parse_iso8601_utc as _parse_iso8601_utc,
    )
    from scripts.security_evidence_utils import (
        resolve_latest_evidence_path as _resolve_latest_evidence_path_impl,
    )
except ModuleNotFoundError:  # pragma: no cover - script execution fallback
    from security_evidence_utils import (
        is_non_negative_int as _is_non_negative_int,
    )
    from security_evidence_utils import (
        parse_iso8601 as _parse_iso8601,
    )
    from security_evidence_utils import (
        parse_iso8601_utc as _parse_iso8601_utc,
    )
    from security_evidence_utils import (
        resolve_latest_evidence_path as _resolve_latest_evidence_path_impl,
    )

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
EVIDENCE_DIR = REPO_ROOT / "docs" / "security" / "evidence"
EVIDENCE_SCHEMA_VERSION = "1.1.0"
P0_DRILL_ARTIFACT_KIND = "p0-drill"
P0_DRILL_GENERATED_BY = "backend/scripts/run_p0_drills.py"
DATA_RIGHTS_FIRE_DRILL_KIND = "data-rights-fire-drill"
BILLING_FIRE_DRILL_KIND = "billing-fire-drill"
BILLING_RECON_ARTIFACT_KIND = "billing-reconciliation"
BILLING_RECON_GENERATED_BY = "backend/scripts/run_billing_reconciliation_audit.py"
AUDIT_RETENTION_ARTIFACT_KIND = "audit-log-retention"
AUDIT_RETENTION_GENERATED_BY = "backend/scripts/run_audit_log_retention_audit.py"
BILLING_CONSOLE_DRIFT_ARTIFACT_KIND = "billing-console-drift"
BILLING_CONSOLE_DRIFT_GENERATED_BY = "backend/scripts/run_billing_console_drift_audit.py"
BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "policy_contract_passed",
    "store_compliance_contract_passed",
    "webhook_secret_configured",
    "webhook_tolerance_within_policy",
    "async_mode_within_policy",
    "nonprod_dry_run",
)
DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND = "data-soft-delete-purge"
DATA_SOFT_DELETE_PURGE_GENERATED_BY = "backend/scripts/run_data_soft_delete_purge_audit.py"
KEY_ROTATION_DRILL_ARTIFACT_KIND = "key-rotation-drill"
KEY_ROTATION_DRILL_GENERATED_BY = "backend/scripts/run_key_rotation_drill_audit.py"
KEY_ROTATION_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "policy_contract_passed",
    "env_separation_enforced",
    "rollback_plan_present",
    "nonprod_dry_run",
)
DATA_RESTORE_DRILL_ARTIFACT_KIND = "data-restore-drill"
DATA_RESTORE_DRILL_GENERATED_BY = "backend/scripts/run_data_restore_drill_audit.py"
DATA_RESTORE_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "rollback_plan_present",
    "lifecycle_contract_passed",
    "source_purge_evidence_fresh",
    "nonprod_dry_run",
)
BACKUP_RESTORE_DRILL_ARTIFACT_KIND = "backup-restore-drill"
BACKUP_RESTORE_DRILL_GENERATED_BY = "backend/scripts/run_backup_restore_drill_audit.py"
BACKUP_RESTORE_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "rollback_plan_present",
    "backup_policy_present",
    "encryption_policy_enforced",
    "restore_workflow_declared",
    "source_restore_evidence_fresh",
    "nonprod_dry_run",
)
CHAOS_DRILL_ARTIFACT_KIND = "chaos-drill"
CHAOS_DRILL_GENERATED_BY = "backend/scripts/run_chaos_drill_audit.py"
CHAOS_DRILL_REQUIRED_DRILLS: tuple[str, ...] = (
    "ai_provider_outage",
    "ws_storm",
)
CHAOS_DRILL_REQUIRED_CHECKS: tuple[str, ...] = (
    "runbook_present",
    "incident_playbook_ai_outage_present",
    "incident_playbook_ws_storm_present",
    "report_template_present",
    "workflow_schedule_declared",
    "nonprod_dry_run",
)
DATA_SOFT_DELETE_PURGE_COUNT_KEYS: tuple[str, ...] = (
    "analyses",
    "journals",
    "card_responses",
    "card_sessions",
    "notification_events",
    "users",
)
CONTRACT_MODE_STRICT = "strict"
CONTRACT_MODE_COMPAT = "compat"

REQUIRED_P0_DRILL_CHECKS: set[str] = {
    "data_rights_export_scope",
    "data_rights_erase_integrity",
    "data_rights_audit_trail",
    "billing_state_change_idempotency",
    "billing_reconciliation_health",
    "billing_webhook_binding_resolution",
    "billing_webhook_identifier_conflict_guard",
    "billing_webhook_transition_guard",
    "billing_webhook_replay_safety",
}
REQUIRED_DATA_RIGHTS_DRILL_CHECKS: set[str] = {
    "data_rights_export_scope",
    "data_rights_erase_integrity",
    "data_rights_audit_trail",
}
REQUIRED_BILLING_DRILL_CHECKS: set[str] = {
    "billing_state_change_idempotency",
    "billing_reconciliation_health",
    "billing_webhook_binding_resolution",
    "billing_webhook_identifier_conflict_guard",
    "billing_webhook_transition_guard",
    "billing_webhook_replay_safety",
}
DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS: tuple[str, ...] = (
    DATA_RIGHTS_FIRE_DRILL_KIND,
    P0_DRILL_ARTIFACT_KIND,
)
BILLING_ACCEPTED_ARTIFACT_KINDS: tuple[str, ...] = (
    BILLING_FIRE_DRILL_KIND,
    P0_DRILL_ARTIFACT_KIND,
)


def _resolve_latest_evidence_path(kind: str) -> Path:
    """Backwards-compatible wrapper retained for existing contract tests."""
    return _resolve_latest_evidence_path_impl(evidence_dir=EVIDENCE_DIR, kind=kind)

def validate_p0_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind not in DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS:
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS)} (got `{artifact_kind}`)."
            )
        if generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if (
            artifact_kind is not None
            and artifact_kind not in DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS
        ):
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS)} when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")

    if contract_mode == CONTRACT_MODE_STRICT:
        if not isinstance(required_checks, list):
            errors.append("`required_checks` must be a list.")
        elif required_checks != sorted(REQUIRED_P0_DRILL_CHECKS):
            errors.append(
                f"`required_checks` must equal sorted required checks: {sorted(REQUIRED_P0_DRILL_CHECKS)}"
            )
    elif required_checks is not None:
        if not isinstance(required_checks, list) or not all(
            isinstance(item, str) and item.strip() for item in required_checks
        ):
            errors.append(
                "`required_checks` must be a list of non-empty strings when present in compat validation."
            )

    enforce_check_counters = contract_mode == CONTRACT_MODE_STRICT or any(
        value is not None for value in (checks_total, checks_passed, checks_failed)
    )
    if enforce_check_counters:
        if not _is_non_negative_int(checks_total):
            errors.append("`checks_total` must be a non-negative integer.")
        if not _is_non_negative_int(checks_passed):
            errors.append("`checks_passed` must be a non-negative integer.")
        if not _is_non_negative_int(checks_failed):
            errors.append("`checks_failed` must be a non-negative integer.")

    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be a boolean.")
    if not isinstance(results, list):
        errors.append("`results` must be a list.")
        return errors
    if not results:
        errors.append("`results` must not be empty.")
        return errors

    result_names: set[str] = set()
    computed_all_passed = True
    computed_checks_passed = 0
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"`results[{index}]` must be an object.")
            computed_all_passed = False
            continue

        name = item.get("name")
        ok = item.get("ok")
        detail = item.get("detail")

        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be a non-empty string.")
        else:
            if name in result_names:
                errors.append(f"Duplicate drill check name: {name}")
            result_names.add(name)

        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be a boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_checks_passed += 1

        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be a non-empty string.")

    if contract_mode == CONTRACT_MODE_STRICT:
        missing_required = sorted(REQUIRED_P0_DRILL_CHECKS - result_names)
        if missing_required:
            errors.append(f"Missing required drill checks: {missing_required}")
    elif isinstance(required_checks, list):
        normalized_required_checks = sorted(set(required_checks))
        normalized_result_names = sorted(result_names)
        if normalized_required_checks != normalized_result_names:
            errors.append(
                "`required_checks` must match sorted unique `results[].name` in compat validation."
            )

    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )

    if enforce_check_counters:
        computed_checks_total = len(results)
        computed_checks_failed = computed_checks_total - computed_checks_passed
        if isinstance(checks_total, int) and checks_total != computed_checks_total:
            errors.append(
                f"`checks_total` mismatch: payload={checks_total} computed={computed_checks_total}"
            )
        if isinstance(checks_passed, int) and checks_passed != computed_checks_passed:
            errors.append(
                f"`checks_passed` mismatch: payload={checks_passed} computed={computed_checks_passed}"
            )
        if isinstance(checks_failed, int) and checks_failed != computed_checks_failed:
            errors.append(
                f"`checks_failed` mismatch: payload={checks_failed} computed={computed_checks_failed}"
            )
        if (
            isinstance(checks_total, int)
            and isinstance(checks_passed, int)
            and isinstance(checks_failed, int)
            and checks_passed + checks_failed != checks_total
        ):
            errors.append("`checks_passed + checks_failed` must equal `checks_total`.")

    return errors


def validate_data_rights_fire_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind not in DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS:
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS)} (got `{artifact_kind}`)."
            )
        if generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if (
            artifact_kind is not None
            and artifact_kind not in DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS
        ):
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(DATA_RIGHTS_ACCEPTED_ARTIFACT_KINDS)} when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    shared_shape_payload = dict(payload)
    shared_shape_payload.pop("artifact_kind", None)
    errors.extend(
        validate_p0_drill_payload(shared_shape_payload, contract_mode=CONTRACT_MODE_COMPAT)
    )
    if not isinstance(results, list):
        return errors

    results_by_name: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            results_by_name[name] = item

    missing_checks = sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS - set(results_by_name))
    if missing_checks:
        errors.append(f"Missing required data-rights drill checks: {missing_checks}")

    for check_name in sorted(REQUIRED_DATA_RIGHTS_DRILL_CHECKS):
        result_row = results_by_name.get(check_name)
        if result_row is None:
            continue
        if result_row.get("ok") is not True:
            errors.append(f"Data-rights drill check `{check_name}` must pass (`ok=true`).")

    return errors


def validate_billing_fire_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind not in BILLING_ACCEPTED_ARTIFACT_KINDS:
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(BILLING_ACCEPTED_ARTIFACT_KINDS)} (got `{artifact_kind}`)."
            )
        if generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if (
            artifact_kind is not None
            and artifact_kind not in BILLING_ACCEPTED_ARTIFACT_KINDS
        ):
            errors.append(
                "`artifact_kind` must be one of "
                f"{sorted(BILLING_ACCEPTED_ARTIFACT_KINDS)} when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != P0_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{P0_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    shared_shape_payload = dict(payload)
    shared_shape_payload.pop("artifact_kind", None)
    errors.extend(validate_p0_drill_payload(shared_shape_payload, contract_mode=CONTRACT_MODE_COMPAT))
    if not isinstance(results, list):
        return errors

    results_by_name: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name.strip():
            results_by_name[name] = item

    missing_checks = sorted(REQUIRED_BILLING_DRILL_CHECKS - set(results_by_name))
    if missing_checks:
        errors.append(f"Missing required billing drill checks: {missing_checks}")

    for check_name in sorted(REQUIRED_BILLING_DRILL_CHECKS):
        result_row = results_by_name.get(check_name)
        if result_row is None:
            continue
        if result_row.get("ok") is not True:
            errors.append(f"Billing drill check `{check_name}` must pass (`ok=true`).")

    return errors


def validate_billing_reconciliation_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    total_users = payload.get("total_users")
    healthy_users = payload.get("healthy_users")
    unhealthy_users = payload.get("unhealthy_users")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != BILLING_RECON_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{BILLING_RECON_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != BILLING_RECON_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BILLING_RECON_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != BILLING_RECON_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{BILLING_RECON_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != BILLING_RECON_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BILLING_RECON_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not _is_non_negative_int(total_users):
        errors.append("`total_users` must be a non-negative integer.")
    if not _is_non_negative_int(healthy_users):
        errors.append("`healthy_users` must be a non-negative integer.")
    if not _is_non_negative_int(unhealthy_users):
        errors.append("`unhealthy_users` must be a non-negative integer.")
    if not isinstance(results, list):
        errors.append("`results` must be a list.")
        return errors

    if isinstance(total_users, int) and total_users != len(results):
        errors.append(
            f"`total_users` mismatch: payload={total_users} results_len={len(results)}"
        )
    if (
        isinstance(total_users, int)
        and isinstance(healthy_users, int)
        and isinstance(unhealthy_users, int)
        and healthy_users + unhealthy_users != total_users
    ):
        errors.append("`healthy_users + unhealthy_users` must equal `total_users`.")

    computed_healthy_users = 0
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"`results[{index}]` must be an object.")
            continue

        user_id = item.get("user_id")
        command_count = item.get("command_count")
        command_ledger_count = item.get("command_ledger_count")
        missing_count = item.get("missing_command_ledger_count")
        missing_ids = item.get("missing_command_ids")
        entitlement_state = item.get("entitlement_state")
        entitlement_plan = item.get("entitlement_plan")
        healthy = item.get("healthy")

        if not isinstance(user_id, str):
            errors.append(f"`results[{index}].user_id` must be a string UUID.")
        else:
            try:
                uuid.UUID(user_id)
            except ValueError:
                errors.append(f"`results[{index}].user_id` is not a valid UUID: {user_id}")

        if not _is_non_negative_int(command_count):
            errors.append(f"`results[{index}].command_count` must be a non-negative integer.")
        if not _is_non_negative_int(command_ledger_count):
            errors.append(
                f"`results[{index}].command_ledger_count` must be a non-negative integer."
            )
        if not _is_non_negative_int(missing_count):
            errors.append(
                f"`results[{index}].missing_command_ledger_count` must be a non-negative integer."
            )
        if not isinstance(missing_ids, list) or not all(isinstance(v, str) for v in missing_ids):
            errors.append(
                f"`results[{index}].missing_command_ids` must be a list of string command IDs."
            )
        if entitlement_state is not None and not isinstance(entitlement_state, str):
            errors.append(f"`results[{index}].entitlement_state` must be string|null.")
        if entitlement_plan is not None and not isinstance(entitlement_plan, str):
            errors.append(f"`results[{index}].entitlement_plan` must be string|null.")

        if not isinstance(healthy, bool):
            errors.append(f"`results[{index}].healthy` must be a boolean.")
        else:
            if healthy:
                computed_healthy_users += 1

        if (
            isinstance(command_count, int)
            and isinstance(command_ledger_count, int)
            and command_ledger_count > command_count
        ):
            errors.append(
                f"`results[{index}]`: command_ledger_count cannot exceed command_count."
            )

        if (
            isinstance(missing_count, int)
            and isinstance(missing_ids, list)
            and missing_count != len(missing_ids)
        ):
            errors.append(
                f"`results[{index}]`: missing_command_ledger_count does not match missing_command_ids length."
            )

    if isinstance(healthy_users, int) and healthy_users != computed_healthy_users:
        errors.append(
            f"`healthy_users` mismatch: payload={healthy_users} computed={computed_healthy_users}"
        )

    return errors


def validate_audit_retention_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    retention_days = payload.get("retention_days")
    before_count = payload.get("before_count")
    deleted_count = payload.get("deleted_count")
    after_count = payload.get("after_count")
    healthy = payload.get("healthy")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != AUDIT_RETENTION_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{AUDIT_RETENTION_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != AUDIT_RETENTION_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{AUDIT_RETENTION_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != AUDIT_RETENTION_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{AUDIT_RETENTION_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != AUDIT_RETENTION_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{AUDIT_RETENTION_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not _is_non_negative_int(retention_days) or int(retention_days) <= 0:
        errors.append("`retention_days` must be a positive integer.")
    if not _is_non_negative_int(before_count):
        errors.append("`before_count` must be a non-negative integer.")
    if not _is_non_negative_int(deleted_count):
        errors.append("`deleted_count` must be a non-negative integer.")
    if not _is_non_negative_int(after_count):
        errors.append("`after_count` must be a non-negative integer.")
    if not isinstance(healthy, bool):
        errors.append("`healthy` must be a boolean.")

    if (
        isinstance(before_count, int)
        and isinstance(deleted_count, int)
        and deleted_count > before_count
    ):
        errors.append("`deleted_count` cannot be greater than `before_count`.")

    if (
        isinstance(before_count, int)
        and isinstance(deleted_count, int)
        and isinstance(after_count, int)
    ):
        computed_after = before_count - deleted_count
        if after_count != computed_after:
            errors.append(
                f"`after_count` mismatch: payload={after_count} computed={computed_after}"
            )
        computed_healthy = deleted_count <= before_count and after_count == computed_after
        if isinstance(healthy, bool) and healthy != computed_healthy:
            errors.append(
                f"`healthy` mismatch: payload={healthy} computed={computed_healthy}"
            )

    return errors


def validate_billing_console_drift_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    dry_run = payload.get("dry_run")
    provider = payload.get("provider")
    runbook_path = payload.get("runbook_path")
    policy_path = payload.get("policy_path")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    runtime = payload.get("runtime")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != BILLING_CONSOLE_DRIFT_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{BILLING_CONSOLE_DRIFT_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != BILLING_CONSOLE_DRIFT_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BILLING_CONSOLE_DRIFT_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if (
            artifact_kind is not None
            and artifact_kind != BILLING_CONSOLE_DRIFT_ARTIFACT_KIND
        ):
            errors.append(
                f"`artifact_kind` must be `{BILLING_CONSOLE_DRIFT_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != BILLING_CONSOLE_DRIFT_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BILLING_CONSOLE_DRIFT_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not isinstance(dry_run, bool):
        errors.append("`dry_run` must be boolean.")
    if not isinstance(provider, str) or not provider.strip():
        errors.append("`provider` must be non-empty string.")
    if not isinstance(runbook_path, str) or not runbook_path.startswith("docs/"):
        errors.append("`runbook_path` must be docs/* path.")
    if not isinstance(policy_path, str) or not policy_path.startswith("docs/"):
        errors.append("`policy_path` must be docs/* path.")
    if not isinstance(runtime, dict):
        errors.append("`runtime` must be an object.")
    else:
        tolerance_seconds = runtime.get("webhook_tolerance_seconds")
        async_mode = runtime.get("webhook_async_mode")
        if not _is_non_negative_int(tolerance_seconds):
            errors.append("`runtime.webhook_tolerance_seconds` must be non-negative integer.")
        if not isinstance(async_mode, bool):
            errors.append("`runtime.webhook_async_mode` must be boolean.")

    if contract_mode == CONTRACT_MODE_STRICT:
        if not isinstance(required_checks, list):
            errors.append("`required_checks` must be list.")
        elif required_checks != list(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS):
            errors.append(
                f"`required_checks` must equal {list(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS)}."
            )

    if not _is_non_negative_int(checks_total):
        errors.append("`checks_total` must be non-negative integer.")
    if not _is_non_negative_int(checks_passed):
        errors.append("`checks_passed` must be non-negative integer.")
    if not _is_non_negative_int(checks_failed):
        errors.append("`checks_failed` must be non-negative integer.")
    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be boolean.")
    if not isinstance(results, list):
        errors.append("`results` must be list.")
        return errors
    if not results:
        errors.append("`results` must not be empty.")
        return errors

    result_names: list[str] = []
    computed_passed = 0
    computed_all_passed = True
    for index, item in enumerate(results):
        if not isinstance(item, dict):
            errors.append(f"`results[{index}]` must be object.")
            computed_all_passed = False
            continue
        name = item.get("name")
        ok = item.get("ok")
        detail = item.get("detail")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be non-empty string.")
        else:
            result_names.append(name)
        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_passed += 1
        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be non-empty string.")

    if sorted(set(result_names)) != sorted(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS):
        errors.append(
            f"`results[].name` must cover exactly {sorted(BILLING_CONSOLE_DRIFT_REQUIRED_CHECKS)}."
        )

    computed_total = len(results)
    computed_failed = computed_total - computed_passed
    if isinstance(checks_total, int) and checks_total != computed_total:
        errors.append(
            f"`checks_total` mismatch: payload={checks_total} computed={computed_total}"
        )
    if isinstance(checks_passed, int) and checks_passed != computed_passed:
        errors.append(
            f"`checks_passed` mismatch: payload={checks_passed} computed={computed_passed}"
        )
    if isinstance(checks_failed, int) and checks_failed != computed_failed:
        errors.append(
            f"`checks_failed` mismatch: payload={checks_failed} computed={computed_failed}"
        )
    if (
        isinstance(checks_total, int)
        and isinstance(checks_passed, int)
        and isinstance(checks_failed, int)
        and checks_passed + checks_failed != checks_total
    ):
        errors.append("`checks_passed + checks_failed` must equal `checks_total`.")
    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )
    return errors


def validate_data_soft_delete_purge_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    mode = payload.get("mode")
    soft_delete_enabled = payload.get("soft_delete_enabled")
    retention_days = payload.get("retention_days")
    cutoff_iso = payload.get("cutoff_iso")
    candidate_counts = payload.get("candidate_counts")
    purged_counts = payload.get("purged_counts")
    total_candidates = payload.get("total_candidates")
    total_purged = payload.get("total_purged")
    healthy = payload.get("healthy")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != DATA_SOFT_DELETE_PURGE_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{DATA_SOFT_DELETE_PURGE_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != DATA_SOFT_DELETE_PURGE_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{DATA_SOFT_DELETE_PURGE_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if mode not in {"dry_run", "apply"}:
        errors.append("`mode` must be `dry_run` or `apply`.")
    if not isinstance(soft_delete_enabled, bool):
        errors.append("`soft_delete_enabled` must be a boolean.")
    if not _is_non_negative_int(retention_days) or int(retention_days) <= 0:
        errors.append("`retention_days` must be a positive integer.")
    if not isinstance(cutoff_iso, str) or not _parse_iso8601(cutoff_iso):
        errors.append("`cutoff_iso` must be an ISO-8601 timestamp string.")
    if not isinstance(healthy, bool):
        errors.append("`healthy` must be a boolean.")

    if not _is_non_negative_int(total_candidates):
        errors.append("`total_candidates` must be a non-negative integer.")
    if not _is_non_negative_int(total_purged):
        errors.append("`total_purged` must be a non-negative integer.")

    if not isinstance(candidate_counts, dict):
        errors.append("`candidate_counts` must be an object.")
        candidate_counts = {}
    if not isinstance(purged_counts, dict):
        errors.append("`purged_counts` must be an object.")
        purged_counts = {}

    computed_total_candidates = 0
    computed_total_purged = 0
    for key in DATA_SOFT_DELETE_PURGE_COUNT_KEYS:
        candidate_value = candidate_counts.get(key)
        purged_value = purged_counts.get(key)
        if not _is_non_negative_int(candidate_value):
            errors.append(f"`candidate_counts.{key}` must be a non-negative integer.")
            continue
        if not _is_non_negative_int(purged_value):
            errors.append(f"`purged_counts.{key}` must be a non-negative integer.")
            continue
        if purged_value > candidate_value:
            errors.append(f"`purged_counts.{key}` cannot exceed `candidate_counts.{key}`.")
        computed_total_candidates += int(candidate_value)
        computed_total_purged += int(purged_value)

    if isinstance(total_candidates, int) and total_candidates != computed_total_candidates:
        errors.append(
            f"`total_candidates` mismatch: payload={total_candidates} computed={computed_total_candidates}"
        )
    if isinstance(total_purged, int) and total_purged != computed_total_purged:
        errors.append(
            f"`total_purged` mismatch: payload={total_purged} computed={computed_total_purged}"
        )

    if mode == "dry_run" and isinstance(total_purged, int) and total_purged != 0:
        errors.append("`total_purged` must be 0 when mode=dry_run.")

    if (
        isinstance(total_candidates, int)
        and isinstance(total_purged, int)
        and total_purged > total_candidates
    ):
        errors.append("`total_purged` cannot exceed `total_candidates`.")

    computed_healthy = (
        isinstance(mode, str)
        and mode in {"dry_run", "apply"}
        and isinstance(total_candidates, int)
        and isinstance(total_purged, int)
        and total_purged <= total_candidates
        and (mode != "dry_run" or total_purged == 0)
    )
    if isinstance(healthy, bool) and healthy != computed_healthy:
        errors.append(f"`healthy` mismatch: payload={healthy} computed={computed_healthy}")

    return errors


def validate_key_rotation_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    dry_run = payload.get("dry_run")
    kms_provider = payload.get("kms_provider")
    runbook_path = payload.get("runbook_path")
    policy_path = payload.get("policy_path")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != KEY_ROTATION_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{KEY_ROTATION_DRILL_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != KEY_ROTATION_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{KEY_ROTATION_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != KEY_ROTATION_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{KEY_ROTATION_DRILL_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != KEY_ROTATION_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{KEY_ROTATION_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not isinstance(dry_run, bool):
        errors.append("`dry_run` must be a boolean.")
    elif not dry_run:
        errors.append("`dry_run` must be true for key-rotation drill evidence.")
    if not isinstance(kms_provider, str) or not kms_provider.strip():
        errors.append("`kms_provider` must be a non-empty string.")
    if not isinstance(runbook_path, str) or not runbook_path.strip():
        errors.append("`runbook_path` must be a non-empty path string.")
    elif not (REPO_ROOT / runbook_path).exists():
        errors.append(f"`runbook_path` not found: {runbook_path}")
    if not isinstance(policy_path, str) or not policy_path.strip():
        errors.append("`policy_path` must be a non-empty path string.")
    elif not (REPO_ROOT / policy_path).exists():
        errors.append(f"`policy_path` not found: {policy_path}")

    if not isinstance(required_checks, list) or not all(
        isinstance(item, str) and item.strip() for item in required_checks
    ):
        errors.append("`required_checks` must be a non-empty list of check names.")
        required_checks_list: list[str] = []
    else:
        required_checks_list = sorted(required_checks)

    expected_required_checks = sorted(KEY_ROTATION_DRILL_REQUIRED_CHECKS)
    if required_checks_list and required_checks_list != expected_required_checks:
        errors.append(
            f"`required_checks` must equal {expected_required_checks} (got {required_checks_list})."
        )

    if not _is_non_negative_int(checks_total):
        errors.append("`checks_total` must be a non-negative integer.")
    if not _is_non_negative_int(checks_passed):
        errors.append("`checks_passed` must be a non-negative integer.")
    if not _is_non_negative_int(checks_failed):
        errors.append("`checks_failed` must be a non-negative integer.")
    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be a boolean.")

    if not isinstance(results, list) or not results:
        errors.append("`results` must be a non-empty list.")
        return errors

    result_names: list[str] = []
    computed_passed = 0
    computed_all_passed = True
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"`results[{index}]` must be an object.")
            computed_all_passed = False
            continue
        name = row.get("name")
        ok = row.get("ok")
        detail = row.get("detail")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be non-empty string.")
        else:
            result_names.append(name)
        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_passed += 1
        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be non-empty string.")

    if sorted(set(result_names)) != expected_required_checks:
        errors.append(
            f"`results[].name` must cover exactly {expected_required_checks}."
        )

    computed_total = len(results)
    computed_failed = computed_total - computed_passed
    if isinstance(checks_total, int) and checks_total != computed_total:
        errors.append(
            f"`checks_total` mismatch: payload={checks_total} computed={computed_total}"
        )
    if isinstance(checks_passed, int) and checks_passed != computed_passed:
        errors.append(
            f"`checks_passed` mismatch: payload={checks_passed} computed={computed_passed}"
        )
    if isinstance(checks_failed, int) and checks_failed != computed_failed:
        errors.append(
            f"`checks_failed` mismatch: payload={checks_failed} computed={computed_failed}"
        )
    if (
        isinstance(checks_total, int)
        and isinstance(checks_passed, int)
        and isinstance(checks_failed, int)
        and checks_passed + checks_failed != checks_total
    ):
        errors.append("`checks_passed + checks_failed` must equal `checks_total`.")
    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )
    return errors


def validate_data_restore_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    dry_run = payload.get("dry_run")
    runbook_path = payload.get("runbook_path")
    policy_path = payload.get("policy_path")
    source_evidence_kind = payload.get("source_evidence_kind")
    source_evidence_path = payload.get("source_evidence_path")
    source_evidence_generated_at = payload.get("source_evidence_generated_at")
    source_evidence_max_age_days = payload.get("source_evidence_max_age_days")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != DATA_RESTORE_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{DATA_RESTORE_DRILL_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != DATA_RESTORE_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{DATA_RESTORE_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != DATA_RESTORE_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{DATA_RESTORE_DRILL_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != DATA_RESTORE_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{DATA_RESTORE_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not isinstance(dry_run, bool):
        errors.append("`dry_run` must be a boolean.")
    elif not dry_run:
        errors.append("`dry_run` must be true for data-restore drill evidence.")
    if not isinstance(runbook_path, str) or not runbook_path.strip():
        errors.append("`runbook_path` must be a non-empty path string.")
    elif not (REPO_ROOT / runbook_path).exists():
        errors.append(f"`runbook_path` not found: {runbook_path}")
    if not isinstance(policy_path, str) or not policy_path.strip():
        errors.append("`policy_path` must be a non-empty path string.")
    elif not (REPO_ROOT / policy_path).exists():
        errors.append(f"`policy_path` not found: {policy_path}")

    if source_evidence_kind != DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND:
        errors.append(
            f"`source_evidence_kind` must be `{DATA_SOFT_DELETE_PURGE_ARTIFACT_KIND}` (got `{source_evidence_kind}`)."
        )
    if not isinstance(source_evidence_path, str) or not source_evidence_path.strip():
        errors.append("`source_evidence_path` must be a non-empty path string.")
    elif not (REPO_ROOT / source_evidence_path).exists():
        errors.append(f"`source_evidence_path` not found: {source_evidence_path}")
    if not isinstance(source_evidence_generated_at, str) or not _parse_iso8601(source_evidence_generated_at):
        errors.append("`source_evidence_generated_at` must be an ISO-8601 timestamp string.")
    if not _is_non_negative_int(source_evidence_max_age_days) or int(source_evidence_max_age_days) <= 0:
        errors.append("`source_evidence_max_age_days` must be a positive integer.")

    if not isinstance(required_checks, list) or not all(
        isinstance(item, str) and item.strip() for item in required_checks
    ):
        errors.append("`required_checks` must be a non-empty list of check names.")
        required_checks_list: list[str] = []
    else:
        required_checks_list = sorted(required_checks)

    expected_required_checks = sorted(DATA_RESTORE_DRILL_REQUIRED_CHECKS)
    if required_checks_list and required_checks_list != expected_required_checks:
        errors.append(
            f"`required_checks` must equal {expected_required_checks} (got {required_checks_list})."
        )

    if not _is_non_negative_int(checks_total):
        errors.append("`checks_total` must be a non-negative integer.")
    if not _is_non_negative_int(checks_passed):
        errors.append("`checks_passed` must be a non-negative integer.")
    if not _is_non_negative_int(checks_failed):
        errors.append("`checks_failed` must be a non-negative integer.")
    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be a boolean.")

    if not isinstance(results, list) or not results:
        errors.append("`results` must be a non-empty list.")
        return errors

    result_names: list[str] = []
    computed_passed = 0
    computed_all_passed = True
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"`results[{index}]` must be an object.")
            computed_all_passed = False
            continue
        name = row.get("name")
        ok = row.get("ok")
        detail = row.get("detail")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be non-empty string.")
        else:
            result_names.append(name)
        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_passed += 1
        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be non-empty string.")

    if sorted(set(result_names)) != expected_required_checks:
        errors.append(
            f"`results[].name` must cover exactly {expected_required_checks}."
        )

    computed_total = len(results)
    computed_failed = computed_total - computed_passed
    if isinstance(checks_total, int) and checks_total != computed_total:
        errors.append(
            f"`checks_total` mismatch: payload={checks_total} computed={computed_total}"
        )
    if isinstance(checks_passed, int) and checks_passed != computed_passed:
        errors.append(
            f"`checks_passed` mismatch: payload={checks_passed} computed={computed_passed}"
        )
    if isinstance(checks_failed, int) and checks_failed != computed_failed:
        errors.append(
            f"`checks_failed` mismatch: payload={checks_failed} computed={computed_failed}"
        )
    if (
        isinstance(checks_total, int)
        and isinstance(checks_passed, int)
        and isinstance(checks_failed, int)
        and checks_passed + checks_failed != checks_total
    ):
        errors.append("`checks_passed + checks_failed` must equal `checks_total`.")
    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )
    return errors


def validate_backup_restore_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    dry_run = payload.get("dry_run")
    runbook_path = payload.get("runbook_path")
    policy_path = payload.get("policy_path")
    source_evidence_kind = payload.get("source_evidence_kind")
    source_evidence_path = payload.get("source_evidence_path")
    source_evidence_generated_at = payload.get("source_evidence_generated_at")
    source_evidence_max_age_days = payload.get("source_evidence_max_age_days")
    backup_encryption_required = payload.get("backup_encryption_required")
    backup_retention_days = payload.get("backup_retention_days")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != BACKUP_RESTORE_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{BACKUP_RESTORE_DRILL_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != BACKUP_RESTORE_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BACKUP_RESTORE_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != BACKUP_RESTORE_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{BACKUP_RESTORE_DRILL_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != BACKUP_RESTORE_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{BACKUP_RESTORE_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not isinstance(dry_run, bool):
        errors.append("`dry_run` must be a boolean.")
    elif not dry_run:
        errors.append("`dry_run` must be true for backup-restore drill evidence.")
    if not isinstance(runbook_path, str) or not runbook_path.strip():
        errors.append("`runbook_path` must be a non-empty path string.")
    elif not (REPO_ROOT / runbook_path).exists():
        errors.append(f"`runbook_path` not found: {runbook_path}")
    if not isinstance(policy_path, str) or not policy_path.strip():
        errors.append("`policy_path` must be a non-empty path string.")
    elif not (REPO_ROOT / policy_path).exists():
        errors.append(f"`policy_path` not found: {policy_path}")

    if source_evidence_kind != DATA_RESTORE_DRILL_ARTIFACT_KIND:
        errors.append(
            f"`source_evidence_kind` must be `{DATA_RESTORE_DRILL_ARTIFACT_KIND}` (got `{source_evidence_kind}`)."
        )
    if not isinstance(source_evidence_path, str) or not source_evidence_path.strip():
        errors.append("`source_evidence_path` must be a non-empty path string.")
    elif not (REPO_ROOT / source_evidence_path).exists():
        errors.append(f"`source_evidence_path` not found: {source_evidence_path}")
    if not isinstance(source_evidence_generated_at, str) or not _parse_iso8601(source_evidence_generated_at):
        errors.append("`source_evidence_generated_at` must be an ISO-8601 timestamp string.")
    if not _is_non_negative_int(source_evidence_max_age_days) or int(source_evidence_max_age_days) <= 0:
        errors.append("`source_evidence_max_age_days` must be a positive integer.")

    if not isinstance(backup_encryption_required, bool):
        errors.append("`backup_encryption_required` must be a boolean.")
    elif not backup_encryption_required:
        errors.append("`backup_encryption_required` must be true.")
    if not _is_non_negative_int(backup_retention_days) or int(backup_retention_days) <= 0:
        errors.append("`backup_retention_days` must be a positive integer.")

    if not isinstance(required_checks, list) or not all(
        isinstance(item, str) and item.strip() for item in required_checks
    ):
        errors.append("`required_checks` must be a non-empty list of check names.")
        required_checks_list: list[str] = []
    else:
        required_checks_list = sorted(required_checks)

    expected_required_checks = sorted(BACKUP_RESTORE_DRILL_REQUIRED_CHECKS)
    if required_checks_list and required_checks_list != expected_required_checks:
        errors.append(
            f"`required_checks` must equal {expected_required_checks} (got {required_checks_list})."
        )

    if not _is_non_negative_int(checks_total):
        errors.append("`checks_total` must be a non-negative integer.")
    if not _is_non_negative_int(checks_passed):
        errors.append("`checks_passed` must be a non-negative integer.")
    if not _is_non_negative_int(checks_failed):
        errors.append("`checks_failed` must be a non-negative integer.")
    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be a boolean.")

    if not isinstance(results, list) or not results:
        errors.append("`results` must be a non-empty list.")
        return errors

    result_names: list[str] = []
    computed_passed = 0
    computed_all_passed = True
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"`results[{index}]` must be an object.")
            computed_all_passed = False
            continue
        name = row.get("name")
        ok = row.get("ok")
        detail = row.get("detail")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be non-empty string.")
        else:
            result_names.append(name)
        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_passed += 1
        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be non-empty string.")

    if sorted(set(result_names)) != expected_required_checks:
        errors.append(
            f"`results[].name` must cover exactly {expected_required_checks}."
        )

    computed_total = len(results)
    computed_failed = computed_total - computed_passed
    if isinstance(checks_total, int) and checks_total != computed_total:
        errors.append(
            f"`checks_total` mismatch: payload={checks_total} computed={computed_total}"
        )
    if isinstance(checks_passed, int) and checks_passed != computed_passed:
        errors.append(
            f"`checks_passed` mismatch: payload={checks_passed} computed={computed_passed}"
        )
    if isinstance(checks_failed, int) and checks_failed != computed_failed:
        errors.append(
            f"`checks_failed` mismatch: payload={checks_failed} computed={computed_failed}"
        )
    if (
        isinstance(checks_total, int)
        and isinstance(checks_passed, int)
        and isinstance(checks_failed, int)
        and checks_passed + checks_failed != checks_total
    ):
        errors.append("`checks_passed + checks_failed` must equal `checks_total`.")
    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )
    return errors


def validate_chaos_drill_payload(
    payload: dict[str, Any],
    *,
    contract_mode: str = CONTRACT_MODE_STRICT,
) -> list[str]:
    errors: list[str] = []
    schema_version = payload.get("schema_version")
    artifact_kind = payload.get("artifact_kind")
    generated_by = payload.get("generated_by")
    payload_contract_mode = payload.get("contract_mode")
    generated_at = payload.get("generated_at")
    dry_run = payload.get("dry_run")
    runbook_path = payload.get("runbook_path")
    incident_playbook_path = payload.get("incident_playbook_path")
    report_template_path = payload.get("report_template_path")
    workflow_path = payload.get("workflow_path")
    required_drills = payload.get("required_drills")
    executed_drills = payload.get("executed_drills")
    required_checks = payload.get("required_checks")
    checks_total = payload.get("checks_total")
    checks_passed = payload.get("checks_passed")
    checks_failed = payload.get("checks_failed")
    all_passed = payload.get("all_passed")
    results = payload.get("results")

    if contract_mode not in {CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT}:
        raise ValueError(f"Unsupported contract_mode: {contract_mode}")

    if contract_mode == CONTRACT_MODE_STRICT:
        if schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` (got `{schema_version}`)."
            )
        if artifact_kind != CHAOS_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{CHAOS_DRILL_ARTIFACT_KIND}` (got `{artifact_kind}`)."
            )
        if generated_by != CHAOS_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{CHAOS_DRILL_GENERATED_BY}` (got `{generated_by}`)."
            )
        if payload_contract_mode != CONTRACT_MODE_STRICT:
            errors.append(
                f"`contract_mode` must be `{CONTRACT_MODE_STRICT}` in strict validation (got `{payload_contract_mode}`)."
            )
    else:
        if schema_version is not None and schema_version != EVIDENCE_SCHEMA_VERSION:
            errors.append(
                f"`schema_version` must be `{EVIDENCE_SCHEMA_VERSION}` when present (got `{schema_version}`)."
            )
        if artifact_kind is not None and artifact_kind != CHAOS_DRILL_ARTIFACT_KIND:
            errors.append(
                f"`artifact_kind` must be `{CHAOS_DRILL_ARTIFACT_KIND}` when present (got `{artifact_kind}`)."
            )
        if generated_by is not None and generated_by != CHAOS_DRILL_GENERATED_BY:
            errors.append(
                f"`generated_by` must be `{CHAOS_DRILL_GENERATED_BY}` when present (got `{generated_by}`)."
            )
        if payload_contract_mode is not None and payload_contract_mode not in {
            CONTRACT_MODE_STRICT,
            CONTRACT_MODE_COMPAT,
        }:
            errors.append(
                f"`contract_mode` must be one of `{CONTRACT_MODE_STRICT}|{CONTRACT_MODE_COMPAT}` when present (got `{payload_contract_mode}`)."
            )

    if not isinstance(generated_at, str) or not _parse_iso8601(generated_at):
        errors.append("`generated_at` must be an ISO-8601 timestamp string.")
    if not isinstance(dry_run, bool):
        errors.append("`dry_run` must be a boolean.")
    elif not dry_run:
        errors.append("`dry_run` must be true for chaos drill evidence.")

    for key, value in (
        ("runbook_path", runbook_path),
        ("incident_playbook_path", incident_playbook_path),
        ("report_template_path", report_template_path),
        ("workflow_path", workflow_path),
    ):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"`{key}` must be a non-empty path string.")
        elif not (REPO_ROOT / value).exists():
            errors.append(f"`{key}` not found: {value}")

    expected_drills = sorted(CHAOS_DRILL_REQUIRED_DRILLS)
    if not isinstance(required_drills, list) or not all(
        isinstance(item, str) and item.strip() for item in required_drills
    ):
        errors.append("`required_drills` must be a non-empty list of drill names.")
    elif sorted(required_drills) != expected_drills:
        errors.append(f"`required_drills` must equal {expected_drills}.")

    if not isinstance(executed_drills, list) or not all(
        isinstance(item, str) and item.strip() for item in executed_drills
    ):
        errors.append("`executed_drills` must be a non-empty list of drill names.")
    elif sorted(executed_drills) != expected_drills:
        errors.append(f"`executed_drills` must equal {expected_drills}.")

    if not isinstance(required_checks, list) or not all(
        isinstance(item, str) and item.strip() for item in required_checks
    ):
        errors.append("`required_checks` must be a non-empty list of check names.")
        required_checks_list: list[str] = []
    else:
        required_checks_list = sorted(required_checks)

    expected_required_checks = sorted(CHAOS_DRILL_REQUIRED_CHECKS)
    if required_checks_list and required_checks_list != expected_required_checks:
        errors.append(
            f"`required_checks` must equal {expected_required_checks} (got {required_checks_list})."
        )

    if not _is_non_negative_int(checks_total):
        errors.append("`checks_total` must be a non-negative integer.")
    if not _is_non_negative_int(checks_passed):
        errors.append("`checks_passed` must be a non-negative integer.")
    if not _is_non_negative_int(checks_failed):
        errors.append("`checks_failed` must be a non-negative integer.")
    if not isinstance(all_passed, bool):
        errors.append("`all_passed` must be a boolean.")

    if not isinstance(results, list) or not results:
        errors.append("`results` must be a non-empty list.")
        return errors

    result_names: list[str] = []
    computed_passed = 0
    computed_all_passed = True
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            errors.append(f"`results[{index}]` must be an object.")
            computed_all_passed = False
            continue
        name = row.get("name")
        ok = row.get("ok")
        detail = row.get("detail")
        if not isinstance(name, str) or not name.strip():
            errors.append(f"`results[{index}].name` must be non-empty string.")
        else:
            result_names.append(name)
        if not isinstance(ok, bool):
            errors.append(f"`results[{index}].ok` must be boolean.")
            computed_all_passed = False
        else:
            computed_all_passed = computed_all_passed and ok
            if ok:
                computed_passed += 1
        if not isinstance(detail, str) or not detail.strip():
            errors.append(f"`results[{index}].detail` must be non-empty string.")

    if sorted(set(result_names)) != expected_required_checks:
        errors.append(f"`results[].name` must cover exactly {expected_required_checks}.")

    computed_total = len(results)
    computed_failed = computed_total - computed_passed
    if isinstance(checks_total, int) and checks_total != computed_total:
        errors.append(
            f"`checks_total` mismatch: payload={checks_total} computed={computed_total}"
        )
    if isinstance(checks_passed, int) and checks_passed != computed_passed:
        errors.append(
            f"`checks_passed` mismatch: payload={checks_passed} computed={computed_passed}"
        )
    if isinstance(checks_failed, int) and checks_failed != computed_failed:
        errors.append(
            f"`checks_failed` mismatch: payload={checks_failed} computed={computed_failed}"
        )
    if (
        isinstance(checks_total, int)
        and isinstance(checks_passed, int)
        and isinstance(checks_failed, int)
        and checks_passed + checks_failed != checks_total
    ):
        errors.append("`checks_passed + checks_failed` must equal `checks_total`.")
    if isinstance(all_passed, bool) and all_passed != computed_all_passed:
        errors.append(
            f"`all_passed` mismatch: payload={all_passed} computed={computed_all_passed}"
        )
    return errors


def validate_evidence_freshness(
    payload: dict[str, Any],
    *,
    max_age_days: int,
    now_utc: datetime | None = None,
) -> list[str]:
    if max_age_days <= 0:
        raise ValueError("max_age_days must be greater than 0")

    errors: list[str] = []
    generated_at = payload.get("generated_at")
    if not isinstance(generated_at, str):
        return ["`generated_at` must be present for freshness validation."]

    generated_at_utc = _parse_iso8601_utc(generated_at)
    if generated_at_utc is None:
        return ["`generated_at` must be an ISO-8601 timestamp string for freshness validation."]

    current = now_utc.astimezone(timezone.utc) if now_utc else datetime.now(timezone.utc)
    delta_seconds = (current - generated_at_utc).total_seconds()
    if delta_seconds < 0:
        return ["evidence `generated_at` is in the future."]

    max_age_seconds = float(max_age_days) * 24 * 60 * 60
    if delta_seconds > max_age_seconds:
        age_days = delta_seconds / (24 * 60 * 60)
        errors.append(
            "evidence is stale: "
            f"generated_at={generated_at_utc.isoformat()} "
            f"age_days={age_days:.1f} "
            f"max_age_days={max_age_days}"
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate security evidence schema.")
    parser.add_argument(
        "--kind",
        required=True,
        choices=(
            "p0-drill",
            DATA_RIGHTS_FIRE_DRILL_KIND,
            BILLING_FIRE_DRILL_KIND,
            "billing-reconciliation",
            "billing-console-drift",
            "audit-log-retention",
            "data-soft-delete-purge",
            "key-rotation-drill",
            "data-restore-drill",
            "backup-restore-drill",
            "chaos-drill",
        ),
        help="Evidence artifact kind.",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to JSON evidence file. If omitted, latest file for --kind is used.",
    )
    parser.add_argument(
        "--contract-mode",
        choices=(CONTRACT_MODE_STRICT, CONTRACT_MODE_COMPAT),
        default=CONTRACT_MODE_STRICT,
        help="Validation strictness. `strict` enforces current full schema; `compat` allows legacy payload shape.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        default=None,
        help=(
            "Optional freshness gate. Fails when evidence generated_at is older than this many days."
        ),
    )
    args = parser.parse_args()

    target_path = (
        args.path
        if args.path
        else _resolve_latest_evidence_path(args.kind)
    )
    if not target_path.exists():
        print(f"[evidence-validate] fail: file not found: {target_path}")
        return 1

    try:
        payload = json.loads(target_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[evidence-validate] fail: invalid JSON: {target_path} ({exc})")
        return 1

    if not isinstance(payload, dict):
        print(f"[evidence-validate] fail: root payload must be an object: {target_path}")
        return 1

    if args.kind == "p0-drill":
        errors = validate_p0_drill_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == DATA_RIGHTS_FIRE_DRILL_KIND:
        errors = validate_data_rights_fire_drill_payload(
            payload,
            contract_mode=args.contract_mode,
        )
    elif args.kind == BILLING_FIRE_DRILL_KIND:
        errors = validate_billing_fire_drill_payload(
            payload,
            contract_mode=args.contract_mode,
        )
    elif args.kind == "billing-reconciliation":
        errors = validate_billing_reconciliation_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "billing-console-drift":
        errors = validate_billing_console_drift_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "data-soft-delete-purge":
        errors = validate_data_soft_delete_purge_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "key-rotation-drill":
        errors = validate_key_rotation_drill_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "data-restore-drill":
        errors = validate_data_restore_drill_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "backup-restore-drill":
        errors = validate_backup_restore_drill_payload(payload, contract_mode=args.contract_mode)
    elif args.kind == "chaos-drill":
        errors = validate_chaos_drill_payload(payload, contract_mode=args.contract_mode)
    else:
        errors = validate_audit_retention_payload(payload, contract_mode=args.contract_mode)

    if args.max_age_days is not None:
        try:
            freshness_errors = validate_evidence_freshness(
                payload,
                max_age_days=args.max_age_days,
            )
        except ValueError as exc:
            print(f"[evidence-validate] fail: invalid --max-age-days ({exc})")
            return 1
        errors.extend(freshness_errors)

    if errors:
        print(f"[evidence-validate] kind={args.kind} path={target_path} result=fail")
        for err in errors:
            print(f"  - {err}")
        return 1

    print(f"[evidence-validate] kind={args.kind} path={target_path} result=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
