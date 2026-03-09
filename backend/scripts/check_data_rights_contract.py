#!/usr/bin/env python3
"""Policy-as-code gate for data-rights export/erase contract artifacts."""

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

from app.api.routers.users import DATA_ERASE_COUNT_KEYS, DATA_EXPORT_SECTION_KEYS  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.schemas.user import DataExportPackagePublic  # noqa: E402

EXPORT_SPEC_SCHEMA_VERSION = "1.0.0"
EXPORT_SPEC_ARTIFACT_KIND = "data-rights-export-package-spec"
EXPORT_SPEC_PATH = REPO_ROOT / "docs" / "security" / "data-rights-export-package-spec.json"

DELETION_GRAPH_SCHEMA_VERSION = "1.0.0"
DELETION_GRAPH_ARTIFACT_KIND = "data-rights-deletion-graph"
DELETION_GRAPH_PATH = REPO_ROOT / "docs" / "security" / "data-rights-deletion-graph.json"

EXPORT_ENDPOINT = "/api/users/me/data-export"
ERASE_ENDPOINT = "/api/users/me/data"
EXPECTED_EXPORT_META_FIELDS = ("export_version", "exported_at", "expires_at")
EXPECTED_EXPORT_VERSION = "v1"

DELETION_KEY_TO_RESOURCE = {
    "analyses": "analysis",
    "journals": "journal",
    "card_responses": "card_response",
    "card_sessions": "card_session",
    "notification_events": "notification_event",
    "users": "user",
}


@dataclass(frozen=True)
class DataRightsContractViolation:
    domain: str
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_data_rights_contract_violations(
    *,
    export_spec_payload: dict[str, Any] | None = None,
    deletion_graph_payload: dict[str, Any] | None = None,
    export_section_keys: tuple[str, ...] = DATA_EXPORT_SECTION_KEYS,
    erase_count_keys: tuple[str, ...] = DATA_ERASE_COUNT_KEYS,
    export_version: str = EXPECTED_EXPORT_VERSION,
    export_expiry_days: int = settings.DATA_EXPORT_EXPIRY_DAYS,
) -> list[DataRightsContractViolation]:
    export_spec = export_spec_payload if export_spec_payload is not None else _load_json(EXPORT_SPEC_PATH)
    deletion_graph = (
        deletion_graph_payload if deletion_graph_payload is not None else _load_json(DELETION_GRAPH_PATH)
    )

    violations: list[DataRightsContractViolation] = []

    if export_spec.get("schema_version") != EXPORT_SPEC_SCHEMA_VERSION:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{EXPORT_SPEC_SCHEMA_VERSION}` "
                    f"(got `{export_spec.get('schema_version')}`)."
                ),
            )
        )

    if export_spec.get("artifact_kind") != EXPORT_SPEC_ARTIFACT_KIND:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{EXPORT_SPEC_ARTIFACT_KIND}` "
                    f"(got `{export_spec.get('artifact_kind')}`)."
                ),
            )
        )

    if export_spec.get("endpoint") != EXPORT_ENDPOINT:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="invalid_endpoint",
                details=f"endpoint must be `{EXPORT_ENDPOINT}`.",
            )
        )

    if export_spec.get("export_version") != export_version:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="export_version_mismatch",
                details=(
                    f"export_version mismatch: spec=`{export_spec.get('export_version')}` "
                    f"code=`{export_version}`"
                ),
            )
        )

    expiry_days = export_spec.get("expires_after_days_default")
    if not isinstance(expiry_days, int) or expiry_days <= 0:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="invalid_expires_after_days_default",
                details="expires_after_days_default must be a positive integer.",
            )
        )
    elif expiry_days != export_expiry_days:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="expiry_days_mismatch",
                details=(
                    f"expires_after_days_default mismatch: spec={expiry_days} "
                    f"code={export_expiry_days}"
                ),
            )
        )

    sections = export_spec.get("sections")
    if not isinstance(sections, list) or not sections:
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="invalid_sections",
                details="sections must be a non-empty list.",
            )
        )
        section_names: list[str] = []
    else:
        section_names = []
        for index, section in enumerate(sections):
            if not isinstance(section, dict):
                violations.append(
                    DataRightsContractViolation(
                        domain="export_spec",
                        reason="invalid_section_entry",
                        details=f"sections[{index}] must be an object.",
                    )
                )
                continue
            name = section.get("name")
            required = section.get("required")
            owner_scope = section.get("owner_scope")
            if not isinstance(name, str) or not name.strip():
                violations.append(
                    DataRightsContractViolation(
                        domain="export_spec",
                        reason="invalid_section_name",
                        details=f"sections[{index}].name must be a non-empty string.",
                    )
                )
                continue
            section_names.append(name.strip())
            if not isinstance(required, bool) or required is not True:
                violations.append(
                    DataRightsContractViolation(
                        domain="export_spec",
                        reason="invalid_section_required",
                        details=f"sections[{index}].required must be true.",
                    )
                )
            if not isinstance(owner_scope, str) or not owner_scope.strip():
                violations.append(
                    DataRightsContractViolation(
                        domain="export_spec",
                        reason="invalid_section_owner_scope",
                        details=f"sections[{index}].owner_scope must be a non-empty string.",
                    )
                )

        if len(section_names) != len(set(section_names)):
            violations.append(
                DataRightsContractViolation(
                    domain="export_spec",
                    reason="duplicate_section_name",
                    details="section names must be unique.",
                )
            )

    section_tuple = tuple(section_names)
    if section_tuple and section_tuple != tuple(export_section_keys):
        violations.append(
            DataRightsContractViolation(
                domain="export_spec",
                reason="section_order_mismatch",
                details=(
                    f"sections mismatch: spec={list(section_tuple)} "
                    f"code={list(export_section_keys)}"
                ),
            )
        )

    export_model_fields = tuple(DataExportPackagePublic.model_fields.keys())
    expected_fields = (*EXPECTED_EXPORT_META_FIELDS, *export_section_keys)
    if export_model_fields != expected_fields:
        violations.append(
            DataRightsContractViolation(
                domain="export_schema",
                reason="export_model_fields_mismatch",
                details=(
                    f"DataExportPackagePublic fields mismatch: "
                    f"model={list(export_model_fields)} expected={list(expected_fields)}"
                ),
            )
        )

    export_version_default = DataExportPackagePublic.model_fields["export_version"].default
    if export_version_default != export_version:
        violations.append(
            DataRightsContractViolation(
                domain="export_schema",
                reason="export_version_default_mismatch",
                details=(
                    f"DataExportPackagePublic.export_version default must be `{export_version}` "
                    f"(got `{export_version_default}`)."
                ),
            )
        )

    if deletion_graph.get("schema_version") != DELETION_GRAPH_SCHEMA_VERSION:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{DELETION_GRAPH_SCHEMA_VERSION}` "
                    f"(got `{deletion_graph.get('schema_version')}`)."
                ),
            )
        )

    if deletion_graph.get("artifact_kind") != DELETION_GRAPH_ARTIFACT_KIND:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{DELETION_GRAPH_ARTIFACT_KIND}` "
                    f"(got `{deletion_graph.get('artifact_kind')}`)."
                ),
            )
        )

    if deletion_graph.get("endpoint") != ERASE_ENDPOINT:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_endpoint",
                details=f"endpoint must be `{ERASE_ENDPOINT}`.",
            )
        )

    deleted_count_keys = deletion_graph.get("deleted_count_keys")
    if not isinstance(deleted_count_keys, list) or not deleted_count_keys:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_deleted_count_keys",
                details="deleted_count_keys must be a non-empty list.",
            )
        )
        deleted_count_key_tuple: tuple[str, ...] = tuple()
    else:
        deleted_count_key_tuple = tuple(str(value).strip() for value in deleted_count_keys)

    if deleted_count_key_tuple and deleted_count_key_tuple != tuple(erase_count_keys):
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="deleted_count_keys_mismatch",
                details=(
                    f"deleted_count_keys mismatch: spec={list(deleted_count_key_tuple)} "
                    f"code={list(erase_count_keys)}"
                ),
            )
        )

    resources = deletion_graph.get("resources")
    if not isinstance(resources, list) or not resources:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_resources",
                details="resources must be a non-empty list.",
            )
        )
        resource_names: set[str] = set()
    else:
        resource_names = set()
        for index, resource in enumerate(resources):
            if not isinstance(resource, dict):
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_resource_entry",
                        details=f"resources[{index}] must be an object.",
                    )
                )
                continue
            name = resource.get("name")
            delete_mode = resource.get("delete_mode")
            owner_key = resource.get("owner_key")
            if not isinstance(name, str) or not name.strip():
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_resource_name",
                        details=f"resources[{index}].name must be a non-empty string.",
                    )
                )
                continue
            normalized_name = name.strip()
            if normalized_name in resource_names:
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="duplicate_resource_name",
                        details=f"duplicate resource name `{normalized_name}`.",
                    )
                )
            resource_names.add(normalized_name)

            if delete_mode != "hard_delete":
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_delete_mode",
                        details=(
                            f"resources[{index}].delete_mode must be `hard_delete` "
                            f"(got `{delete_mode}`)."
                        ),
                    )
                )
            if not isinstance(owner_key, str) or not owner_key.strip():
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_owner_key",
                        details=f"resources[{index}].owner_key must be a non-empty string.",
                    )
                )

    if resource_names:
        for key, resource in DELETION_KEY_TO_RESOURCE.items():
            if key in erase_count_keys and resource not in resource_names:
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="missing_resource_for_deleted_count_key",
                        details=(
                            f"resource `{resource}` required by deleted_count key `{key}` "
                            "is missing."
                        ),
                    )
                )

    edges = deletion_graph.get("edges")
    if not isinstance(edges, list) or not edges:
        violations.append(
            DataRightsContractViolation(
                domain="deletion_graph",
                reason="invalid_edges",
                details="edges must be a non-empty list.",
            )
        )
    else:
        for index, edge in enumerate(edges):
            if not isinstance(edge, dict):
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_edge_entry",
                        details=f"edges[{index}] must be an object.",
                    )
                )
                continue
            edge_from = edge.get("from")
            edge_to = edge.get("to")
            reason = edge.get("reason")
            if not isinstance(edge_from, str) or edge_from not in resource_names:
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_edge_from",
                        details=f"edges[{index}].from must reference a known resource name.",
                    )
                )
            if not isinstance(edge_to, str) or edge_to not in resource_names:
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_edge_to",
                        details=f"edges[{index}].to must reference a known resource name.",
                    )
                )
            if not isinstance(reason, str) or not reason.strip():
                violations.append(
                    DataRightsContractViolation(
                        domain="deletion_graph",
                        reason="invalid_edge_reason",
                        details=f"edges[{index}].reason must be a non-empty string.",
                    )
                )

    return violations


def run_policy_check() -> int:
    violations = collect_data_rights_contract_violations()
    if not violations:
        print("[data-rights-contract] ok: export spec + deletion graph contract satisfied")
        return 0

    print("[data-rights-contract] failed:", file=sys.stderr)
    for item in violations:
        print(
            f"  - domain={item.domain} reason={item.reason} details={item.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
