#!/usr/bin/env python3
"""Policy-as-code gate for data deletion lifecycle (hard-delete -> trash/purge)."""

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
from app.models.analysis import Analysis  # noqa: E402
from app.models.card_response import CardResponse  # noqa: E402
from app.models.card_session import CardSession  # noqa: E402
from app.models.journal import Journal  # noqa: E402
from app.models.notification_event import NotificationEvent  # noqa: E402
from app.models.user import User  # noqa: E402

POLICY_SCHEMA_VERSION = "1.0.0"
POLICY_ARTIFACT_KIND = "data-deletion-lifecycle-policy"
POLICY_PATH = REPO_ROOT / "docs" / "security" / "data-deletion-lifecycle-policy.json"
RETENTION_POLICY_PATH = REPO_ROOT / "docs" / "security" / "data-retention-policy.json"
DELETION_GRAPH_PATH = REPO_ROOT / "docs" / "security" / "data-rights-deletion-graph.json"
USERS_ROUTER_PATH = BACKEND_ROOT / "app" / "api" / "routers" / "users" / "routes.py"

ALLOWED_MODES = frozenset({"hard_delete", "soft_delete_then_purge"})
REQUIRED_AUDIT_ACTIONS = ("USER_DATA_ERASE", "USER_DATA_ERASE_ERROR")
REQUIRED_RUNTIME_SETTINGS = {
    "soft_delete_enabled_env": "DATA_SOFT_DELETE_ENABLED",
    "trash_retention_days_env": "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS",
    "purge_retention_days_env": "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS",
}


@dataclass(frozen=True)
class DataDeletionLifecycleViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_data_deletion_lifecycle_contract_violations(
    *,
    lifecycle_policy_payload: dict[str, Any] | None = None,
    retention_policy_payload: dict[str, Any] | None = None,
    deletion_graph_payload: dict[str, Any] | None = None,
    users_router_source: str | None = None,
    erase_count_keys: tuple[str, ...] = DATA_ERASE_COUNT_KEYS,
    soft_delete_enabled_setting: bool = settings.DATA_SOFT_DELETE_ENABLED,
    soft_delete_trash_retention_days_setting: int = settings.DATA_SOFT_DELETE_TRASH_RETENTION_DAYS,
    soft_delete_purge_retention_days_setting: int = settings.DATA_SOFT_DELETE_PURGE_RETENTION_DAYS,
    model_deleted_at_support: dict[str, bool] | None = None,
) -> list[DataDeletionLifecycleViolation]:
    lifecycle_policy = (
        lifecycle_policy_payload
        if lifecycle_policy_payload is not None
        else _load_json(POLICY_PATH)
    )
    retention_policy = (
        retention_policy_payload
        if retention_policy_payload is not None
        else _load_json(RETENTION_POLICY_PATH)
    )
    deletion_graph = (
        deletion_graph_payload
        if deletion_graph_payload is not None
        else _load_json(DELETION_GRAPH_PATH)
    )
    router_text = users_router_source if users_router_source is not None else USERS_ROUTER_PATH.read_text(encoding="utf-8")
    deleted_at_support = model_deleted_at_support or {
        "analyses": hasattr(Analysis, "deleted_at"),
        "journals": hasattr(Journal, "deleted_at"),
        "card_responses": hasattr(CardResponse, "deleted_at"),
        "card_sessions": hasattr(CardSession, "deleted_at"),
        "notification_events": hasattr(NotificationEvent, "deleted_at"),
        "users": hasattr(User, "deleted_at"),
    }

    violations: list[DataDeletionLifecycleViolation] = []

    if lifecycle_policy.get("schema_version") != POLICY_SCHEMA_VERSION:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{POLICY_SCHEMA_VERSION}` "
                    f"(got `{lifecycle_policy.get('schema_version')}`)."
                ),
            )
        )

    if lifecycle_policy.get("artifact_kind") != POLICY_ARTIFACT_KIND:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{POLICY_ARTIFACT_KIND}` "
                    f"(got `{lifecycle_policy.get('artifact_kind')}`)."
                ),
            )
        )

    default_mode = lifecycle_policy.get("default_mode")
    if default_mode not in ALLOWED_MODES:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_default_mode",
                details=f"default_mode must be one of {sorted(ALLOWED_MODES)}.",
            )
        )

    phase_gate = lifecycle_policy.get("phase_gate")
    if not isinstance(phase_gate, dict):
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_phase_gate",
                details="phase_gate must be an object.",
            )
        )
        phase_gate = {}

    soft_delete_enabled = phase_gate.get("soft_delete_enabled")
    trash_retention_days = phase_gate.get("trash_retention_days")
    purge_retention_days = phase_gate.get("purge_retention_days")

    if not isinstance(soft_delete_enabled, bool):
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_soft_delete_enabled",
                details="phase_gate.soft_delete_enabled must be boolean.",
            )
        )
    elif soft_delete_enabled != soft_delete_enabled_setting:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="soft_delete_enabled_setting_mismatch",
                details=(
                    "phase_gate.soft_delete_enabled mismatch between policy and runtime setting: "
                    f"policy={soft_delete_enabled} runtime={soft_delete_enabled_setting}"
                ),
            )
        )

    for key, value in (
        ("trash_retention_days", trash_retention_days),
        ("purge_retention_days", purge_retention_days),
    ):
        if not isinstance(value, int) or value <= 0:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_phase_gate_days",
                    details=f"phase_gate.{key} must be a positive integer.",
                )
            )

    if isinstance(trash_retention_days, int) and isinstance(purge_retention_days, int):
        if purge_retention_days < trash_retention_days:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_phase_gate_order",
                    details="purge_retention_days must be >= trash_retention_days.",
                )
            )
        if trash_retention_days != soft_delete_trash_retention_days_setting:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="soft_delete_trash_retention_days_setting_mismatch",
                    details=(
                        "phase_gate.trash_retention_days mismatch between policy and runtime setting: "
                        f"policy={trash_retention_days} runtime={soft_delete_trash_retention_days_setting}"
                    ),
                )
            )
        if purge_retention_days != soft_delete_purge_retention_days_setting:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="soft_delete_purge_retention_days_setting_mismatch",
                    details=(
                        "phase_gate.purge_retention_days mismatch between policy and runtime setting: "
                        f"policy={purge_retention_days} runtime={soft_delete_purge_retention_days_setting}"
                    ),
                )
            )

    required_audit_actions = lifecycle_policy.get("required_audit_actions")
    if not isinstance(required_audit_actions, list) or not required_audit_actions:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_required_audit_actions",
                details="required_audit_actions must be a non-empty list.",
            )
        )
        required_audit_actions = []

    if sorted(required_audit_actions) != sorted(REQUIRED_AUDIT_ACTIONS):
        violations.append(
            DataDeletionLifecycleViolation(
                reason="required_audit_actions_mismatch",
                details=(
                    f"required_audit_actions must equal {list(REQUIRED_AUDIT_ACTIONS)} "
                    f"(got {required_audit_actions})."
                ),
            )
        )

    runtime_settings = lifecycle_policy.get("runtime_settings")
    if not isinstance(runtime_settings, dict) or not runtime_settings:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_runtime_settings",
                details="runtime_settings must be a non-empty object.",
            )
        )
    else:
        for key, expected_value in REQUIRED_RUNTIME_SETTINGS.items():
            value = runtime_settings.get(key)
            if value != expected_value:
                violations.append(
                    DataDeletionLifecycleViolation(
                        reason="runtime_settings_mismatch",
                        details=(
                            f"runtime_settings.{key} must be `{expected_value}` "
                            f"(got `{value}`)."
                        ),
                    )
                )

    for action in REQUIRED_AUDIT_ACTIONS:
        if action not in router_text:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="missing_audit_action_in_router",
                    details=f"users router missing audit action `{action}`.",
                )
            )

    resources = lifecycle_policy.get("resources")
    if not isinstance(resources, list) or not resources:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_resources",
                details="resources must be a non-empty list.",
            )
        )
        resources = []

    resource_by_class: dict[str, dict[str, Any]] = {}
    for index, resource in enumerate(resources):
        if not isinstance(resource, dict):
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_resource_entry",
                    details=f"resources[{index}] must be an object.",
                )
            )
            continue

        data_class = str(resource.get("data_class", "")).strip()
        current_mode = str(resource.get("current_delete_mode", "")).strip()
        future_mode = str(resource.get("future_delete_mode", "")).strip()

        if not data_class:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_resource_data_class",
                    details=f"resources[{index}].data_class must be non-empty.",
                )
            )
            continue

        if data_class in resource_by_class:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="duplicate_resource_data_class",
                    details=f"duplicate data_class `{data_class}` in resources.",
                )
            )
            continue

        resource_by_class[data_class] = resource

        if current_mode not in ALLOWED_MODES:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_current_delete_mode",
                    details=f"resource `{data_class}` has invalid current_delete_mode `{current_mode}`.",
                )
            )

        if future_mode not in ALLOWED_MODES:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="invalid_future_delete_mode",
                    details=f"resource `{data_class}` has invalid future_delete_mode `{future_mode}`.",
                )
            )

        if current_mode == "soft_delete_then_purge" or future_mode == "soft_delete_then_purge":
            if deleted_at_support.get(data_class) is not True:
                violations.append(
                    DataDeletionLifecycleViolation(
                        reason="missing_deleted_at_schema_hook",
                        details=(
                            f"data class `{data_class}` requires a `deleted_at` schema hook "
                            "for soft-delete lifecycle."
                        ),
                    )
                )

    for data_class in erase_count_keys:
        if data_class not in resource_by_class:
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="missing_erase_resource",
                    details=f"erase-scoped data class `{data_class}` missing in lifecycle resources.",
                )
            )

    retention_entries = retention_policy.get("policies")
    if not isinstance(retention_entries, list):
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_retention_policy",
                details="retention policy `policies` must be a list.",
            )
        )
        retention_entries = []

    retention_by_class = {
        str(item.get("data_class", "")).strip(): item
        for item in retention_entries
        if isinstance(item, dict)
    }

    if soft_delete_enabled is False:
        for data_class in erase_count_keys:
            resource = resource_by_class.get(data_class)
            if not resource:
                continue
            if resource.get("current_delete_mode") != "hard_delete":
                violations.append(
                    DataDeletionLifecycleViolation(
                        reason="soft_delete_disabled_but_non_hard_delete_resource",
                        details=(
                            f"soft_delete_enabled=false requires `{data_class}` current_delete_mode=hard_delete."
                        ),
                    )
                )

            retention_row = retention_by_class.get(data_class)
            if isinstance(retention_row, dict):
                if retention_row.get("delete_mode") != "hard_delete_on_user_erase":
                    violations.append(
                        DataDeletionLifecycleViolation(
                            reason="retention_mode_mismatch_with_hard_delete_phase",
                            details=(
                                f"`{data_class}` must keep delete_mode=hard_delete_on_user_erase while soft_delete_enabled=false."
                            ),
                        )
                    )

    graph_keys = deletion_graph.get("deleted_count_keys")
    if not isinstance(graph_keys, list):
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_deletion_graph_keys",
                details="deletion graph deleted_count_keys must be a list.",
            )
        )
    else:
        normalized = tuple(str(value).strip() for value in graph_keys)
        if normalized != tuple(erase_count_keys):
            violations.append(
                DataDeletionLifecycleViolation(
                    reason="deletion_graph_keys_mismatch",
                    details=(
                        f"deletion graph keys mismatch: graph={list(normalized)} "
                        f"code={list(erase_count_keys)}"
                    ),
                )
            )

    references = lifecycle_policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            DataDeletionLifecycleViolation(
                reason="invalid_references",
                details="references must be a non-empty object.",
            )
        )
    else:
        for key, value in references.items():
            if not isinstance(value, str) or not value.startswith("docs/"):
                violations.append(
                    DataDeletionLifecycleViolation(
                        reason="invalid_reference_path",
                        details=f"references.{key} must be a docs/* path.",
                    )
                )
                continue
            if not (REPO_ROOT / value).exists():
                violations.append(
                    DataDeletionLifecycleViolation(
                        reason="missing_reference_file",
                        details=f"reference file not found: {value}",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_data_deletion_lifecycle_contract_violations()
    if not violations:
        print("[data-deletion-lifecycle-contract] ok: deletion lifecycle contract satisfied")
        return 0

    print("[data-deletion-lifecycle-contract] failed:", file=sys.stderr)
    for item in violations:
        print(f"  - reason={item.reason} details={item.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
