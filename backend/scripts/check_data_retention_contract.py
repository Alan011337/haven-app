#!/usr/bin/env python3
"""Policy-as-code gate for data retention lifecycle contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.routers.users import DATA_ERASE_COUNT_KEYS  # noqa: E402
from app.core.config import settings  # noqa: E402

RETENTION_POLICY_SCHEMA_VERSION = "1.0.0"
RETENTION_POLICY_ARTIFACT_KIND = "data-retention-policy"
RETENTION_POLICY_PATH = REPO_ROOT / "docs" / "security" / "data-retention-policy.json"
DELETION_GRAPH_PATH = REPO_ROOT / "docs" / "security" / "data-rights-deletion-graph.json"

ALLOWED_DELETE_MODES = frozenset({"purge_job", "ttl_expiry", "hard_delete_on_user_erase"})
ALLOWED_TRIGGERS = frozenset({"scheduled", "time_based", "user_erase"})

AUDIT_DATA_CLASS = "audit_events"
EXPORT_DATA_CLASS = "data_export_packages"


@dataclass(frozen=True)
class DataRetentionContractViolation:
    data_class: str
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_data_retention_contract_violations(
    *,
    retention_policy_payload: dict[str, Any] | None = None,
    deletion_graph_payload: dict[str, Any] | None = None,
    erase_count_keys: tuple[str, ...] = DATA_ERASE_COUNT_KEYS,
    audit_retention_days: int = settings.AUDIT_LOG_RETENTION_DAYS,
    export_expiry_days: int = settings.DATA_EXPORT_EXPIRY_DAYS,
) -> list[DataRetentionContractViolation]:
    policy = (
        retention_policy_payload
        if retention_policy_payload is not None
        else _load_json(RETENTION_POLICY_PATH)
    )
    deletion_graph = (
        deletion_graph_payload
        if deletion_graph_payload is not None
        else _load_json(DELETION_GRAPH_PATH)
    )

    violations: list[DataRetentionContractViolation] = []

    if policy.get("schema_version") != RETENTION_POLICY_SCHEMA_VERSION:
        violations.append(
            DataRetentionContractViolation(
                data_class="*",
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{RETENTION_POLICY_SCHEMA_VERSION}` "
                    f"(got `{policy.get('schema_version')}`)."
                ),
            )
        )

    if policy.get("artifact_kind") != RETENTION_POLICY_ARTIFACT_KIND:
        violations.append(
            DataRetentionContractViolation(
                data_class="*",
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{RETENTION_POLICY_ARTIFACT_KIND}` "
                    f"(got `{policy.get('artifact_kind')}`)."
                ),
            )
        )

    policies = policy.get("policies")
    if not isinstance(policies, list) or not policies:
        violations.append(
            DataRetentionContractViolation(
                data_class="*",
                reason="invalid_policies",
                details="policies must be a non-empty list.",
            )
        )
        return violations

    policy_by_data_class: dict[str, dict[str, Any]] = {}
    for index, entry in enumerate(policies):
        if not isinstance(entry, dict):
            violations.append(
                DataRetentionContractViolation(
                    data_class=f"policies[{index}]",
                    reason="invalid_policy_entry",
                    details="policy entry must be an object.",
                )
            )
            continue

        data_class = str(entry.get("data_class", "")).strip()
        delete_mode = str(entry.get("delete_mode", "")).strip()
        trigger = str(entry.get("trigger", "")).strip()
        retention_days_default = entry.get("retention_days_default")
        retention_days_env = entry.get("retention_days_env")
        owner_team = str(entry.get("owner_team", "")).strip()

        if not data_class:
            violations.append(
                DataRetentionContractViolation(
                    data_class=f"policies[{index}]",
                    reason="invalid_data_class",
                    details="data_class must be a non-empty string.",
                )
            )
            continue

        if data_class in policy_by_data_class:
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="duplicate_data_class",
                    details="data_class must be unique.",
                )
            )
            continue

        policy_by_data_class[data_class] = entry

        if delete_mode not in ALLOWED_DELETE_MODES:
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="invalid_delete_mode",
                    details=f"delete_mode must be one of {sorted(ALLOWED_DELETE_MODES)}.",
                )
            )

        if trigger not in ALLOWED_TRIGGERS:
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="invalid_trigger",
                    details=f"trigger must be one of {sorted(ALLOWED_TRIGGERS)}.",
                )
            )

        if not owner_team:
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="missing_owner_team",
                    details="owner_team must be a non-empty string.",
                )
            )

        if delete_mode in {"purge_job", "ttl_expiry"}:
            if not isinstance(retention_days_default, int) or retention_days_default <= 0:
                violations.append(
                    DataRetentionContractViolation(
                        data_class=data_class,
                        reason="invalid_retention_days_default",
                        details="retention_days_default must be a positive integer.",
                    )
                )
            if not isinstance(retention_days_env, str) or not retention_days_env.strip():
                violations.append(
                    DataRetentionContractViolation(
                        data_class=data_class,
                        reason="invalid_retention_days_env",
                        details="retention_days_env must be a non-empty string.",
                    )
                )

        if delete_mode == "hard_delete_on_user_erase":
            if retention_days_default is not None:
                violations.append(
                    DataRetentionContractViolation(
                        data_class=data_class,
                        reason="hard_delete_retention_days_default_must_be_null",
                        details="retention_days_default must be null for hard_delete_on_user_erase.",
                    )
                )
            if retention_days_env is not None:
                violations.append(
                    DataRetentionContractViolation(
                        data_class=data_class,
                        reason="hard_delete_retention_days_env_must_be_null",
                        details="retention_days_env must be null for hard_delete_on_user_erase.",
                    )
                )

    required_data_classes = {AUDIT_DATA_CLASS, EXPORT_DATA_CLASS, *erase_count_keys}
    missing_required = sorted(required_data_classes - set(policy_by_data_class.keys()))
    for data_class in missing_required:
        violations.append(
            DataRetentionContractViolation(
                data_class=data_class,
                reason="missing_required_data_class",
                details="required data class missing in retention policy.",
            )
        )

    audit_policy = policy_by_data_class.get(AUDIT_DATA_CLASS)
    if audit_policy:
        if audit_policy.get("retention_days_default") != audit_retention_days:
            violations.append(
                DataRetentionContractViolation(
                    data_class=AUDIT_DATA_CLASS,
                    reason="audit_retention_days_mismatch",
                    details=(
                        f"retention_days_default mismatch: policy={audit_policy.get('retention_days_default')} "
                        f"code={audit_retention_days}"
                    ),
                )
            )
        if audit_policy.get("retention_days_env") != "AUDIT_LOG_RETENTION_DAYS":
            violations.append(
                DataRetentionContractViolation(
                    data_class=AUDIT_DATA_CLASS,
                    reason="audit_retention_env_mismatch",
                    details="retention_days_env must be `AUDIT_LOG_RETENTION_DAYS`.",
                )
            )

    export_policy = policy_by_data_class.get(EXPORT_DATA_CLASS)
    if export_policy:
        if export_policy.get("retention_days_default") != export_expiry_days:
            violations.append(
                DataRetentionContractViolation(
                    data_class=EXPORT_DATA_CLASS,
                    reason="export_retention_days_mismatch",
                    details=(
                        f"retention_days_default mismatch: policy={export_policy.get('retention_days_default')} "
                        f"code={export_expiry_days}"
                    ),
                )
            )
        if export_policy.get("retention_days_env") != "DATA_EXPORT_EXPIRY_DAYS":
            violations.append(
                DataRetentionContractViolation(
                    data_class=EXPORT_DATA_CLASS,
                    reason="export_retention_env_mismatch",
                    details="retention_days_env must be `DATA_EXPORT_EXPIRY_DAYS`.",
                )
            )

    for data_class in erase_count_keys:
        entry = policy_by_data_class.get(data_class)
        if not entry:
            continue
        if entry.get("delete_mode") != "hard_delete_on_user_erase":
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="erase_data_class_invalid_delete_mode",
                    details="erase-scoped data class must use hard_delete_on_user_erase.",
                )
            )
        if entry.get("trigger") != "user_erase":
            violations.append(
                DataRetentionContractViolation(
                    data_class=data_class,
                    reason="erase_data_class_invalid_trigger",
                    details="erase-scoped data class trigger must be user_erase.",
                )
            )

    deletion_graph_keys = deletion_graph.get("deleted_count_keys")
    if not isinstance(deletion_graph_keys, list) or not deletion_graph_keys:
        violations.append(
            DataRetentionContractViolation(
                data_class="*",
                reason="invalid_deletion_graph_deleted_count_keys",
                details="deletion graph deleted_count_keys must be a non-empty list.",
            )
        )
    else:
        normalized_graph_keys = tuple(str(item).strip() for item in deletion_graph_keys)
        if normalized_graph_keys != tuple(erase_count_keys):
            violations.append(
                DataRetentionContractViolation(
                    data_class="*",
                    reason="deletion_graph_keys_mismatch",
                    details=(
                        f"deletion graph keys mismatch: graph={list(normalized_graph_keys)} "
                        f"code={list(erase_count_keys)}"
                    ),
                )
            )

    return violations


def run_policy_check() -> int:
    violations = collect_data_retention_contract_violations()
    if not violations:
        print("[data-retention-contract] ok: data retention lifecycle contract satisfied")
        return 0

    print("[data-retention-contract] failed:", file=sys.stderr)
    for item in violations:
        print(
            f"  - data_class={item.data_class} reason={item.reason} details={item.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
