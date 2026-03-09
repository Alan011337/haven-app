#!/usr/bin/env python3
"""Policy-as-code gate for data classification and handling contract."""

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

from scripts.export_api_inventory import DATA_SENSITIVITY_VALUES  # noqa: E402

CLASSIFICATION_POLICY_SCHEMA_VERSION = "1.0.0"
CLASSIFICATION_POLICY_ARTIFACT_KIND = "data-classification-policy"
CLASSIFICATION_POLICY_PATH = REPO_ROOT / "docs" / "security" / "data-classification-policy.json"
INVENTORY_PATH = REPO_ROOT / "docs" / "security" / "api-inventory.json"

EXPECTED_DEFAULT_MAPPING = {
    "public": "non_sensitive",
    "operational": "non_sensitive",
    "account_sensitive": "pii_sensitive",
    "relationship_sensitive": "intimate_sensitive",
    "billing_sensitive": "financial_sensitive",
}

REQUIRED_HANDLING_RULE_FIELDS = (
    "log_redaction_required",
    "encryption_at_rest_required",
    "third_party_transfer_allowed",
    "auditable_access_required",
)

SENSITIVE_DATA_CLASSES = (
    "account_sensitive",
    "relationship_sensitive",
    "billing_sensitive",
)


@dataclass(frozen=True)
class DataClassificationContractViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_data_classification_contract_violations(
    *,
    classification_policy_payload: dict[str, Any] | None = None,
    inventory_payload: dict[str, Any] | None = None,
) -> list[DataClassificationContractViolation]:
    policy = (
        classification_policy_payload
        if classification_policy_payload is not None
        else _load_json(CLASSIFICATION_POLICY_PATH)
    )
    inventory = inventory_payload if inventory_payload is not None else _load_json(INVENTORY_PATH)

    violations: list[DataClassificationContractViolation] = []

    if policy.get("schema_version") != CLASSIFICATION_POLICY_SCHEMA_VERSION:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_schema_version",
                details=(
                    f"schema_version must be `{CLASSIFICATION_POLICY_SCHEMA_VERSION}` "
                    f"(got `{policy.get('schema_version')}`)."
                ),
            )
        )

    if policy.get("artifact_kind") != CLASSIFICATION_POLICY_ARTIFACT_KIND:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_artifact_kind",
                details=(
                    f"artifact_kind must be `{CLASSIFICATION_POLICY_ARTIFACT_KIND}` "
                    f"(got `{policy.get('artifact_kind')}`)."
                ),
            )
        )

    taxonomy = policy.get("taxonomy")
    taxonomy_ids: set[str] = set()
    if not isinstance(taxonomy, list) or not taxonomy:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_taxonomy",
                details="taxonomy must be a non-empty list.",
            )
        )
    else:
        for index, item in enumerate(taxonomy):
            if not isinstance(item, dict):
                violations.append(
                    DataClassificationContractViolation(
                        reason="invalid_taxonomy_entry",
                        details=f"taxonomy[{index}] must be an object.",
                    )
                )
                continue
            taxonomy_id = str(item.get("id", "")).strip()
            description = str(item.get("description", "")).strip()
            if not taxonomy_id:
                violations.append(
                    DataClassificationContractViolation(
                        reason="invalid_taxonomy_id",
                        details=f"taxonomy[{index}].id must be a non-empty string.",
                    )
                )
                continue
            if taxonomy_id in taxonomy_ids:
                violations.append(
                    DataClassificationContractViolation(
                        reason="duplicate_taxonomy_id",
                        details=f"duplicate taxonomy id `{taxonomy_id}`.",
                    )
                )
            taxonomy_ids.add(taxonomy_id)
            if not description:
                violations.append(
                    DataClassificationContractViolation(
                        reason="invalid_taxonomy_description",
                        details=f"taxonomy[{index}].description must be a non-empty string.",
                    )
                )

    mapping = policy.get("sensitivity_mapping")
    if not isinstance(mapping, dict) or not mapping:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_sensitivity_mapping",
                details="sensitivity_mapping must be a non-empty object.",
            )
        )
        mapping = {}

    for sensitivity in sorted(DATA_SENSITIVITY_VALUES):
        target = mapping.get(sensitivity)
        if not isinstance(target, str) or not target.strip():
            violations.append(
                DataClassificationContractViolation(
                    reason="missing_sensitivity_mapping",
                    details=f"missing mapping for `{sensitivity}`.",
                )
            )
            continue
        if taxonomy_ids and target not in taxonomy_ids:
            violations.append(
                DataClassificationContractViolation(
                    reason="mapped_taxonomy_missing",
                    details=f"mapping `{sensitivity}->{target}` references unknown taxonomy id.",
                )
            )

    unknown_mapping_keys = sorted(set(mapping.keys()) - set(DATA_SENSITIVITY_VALUES))
    for key in unknown_mapping_keys:
        violations.append(
            DataClassificationContractViolation(
                reason="unknown_sensitivity_mapping_key",
                details=f"unknown sensitivity mapping key `{key}`.",
            )
        )

    for sensitivity, expected in EXPECTED_DEFAULT_MAPPING.items():
        if mapping.get(sensitivity) != expected:
            violations.append(
                DataClassificationContractViolation(
                    reason="unexpected_default_mapping",
                    details=(
                        f"`{sensitivity}` must map to `{expected}` "
                        f"(got `{mapping.get(sensitivity)}`)."
                    ),
                )
            )

    handling_rules = policy.get("handling_rules")
    if not isinstance(handling_rules, dict) or not handling_rules:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_handling_rules",
                details="handling_rules must be a non-empty object.",
            )
        )
        handling_rules = {}

    for taxonomy_id in sorted(taxonomy_ids):
        rule = handling_rules.get(taxonomy_id)
        if not isinstance(rule, dict):
            violations.append(
                DataClassificationContractViolation(
                    reason="missing_handling_rule",
                    details=f"missing handling rule for taxonomy `{taxonomy_id}`.",
                )
            )
            continue

        for field_name in REQUIRED_HANDLING_RULE_FIELDS:
            value = rule.get(field_name)
            if not isinstance(value, bool):
                violations.append(
                    DataClassificationContractViolation(
                        reason="invalid_handling_rule_field",
                        details=(
                            f"handling_rules.{taxonomy_id}.{field_name} must be a boolean "
                            f"(got `{value}`)."
                        ),
                    )
                )

    for sensitivity in SENSITIVE_DATA_CLASSES:
        taxonomy_id = mapping.get(sensitivity)
        if not isinstance(taxonomy_id, str):
            continue
        rule = handling_rules.get(taxonomy_id)
        if not isinstance(rule, dict):
            continue
        if rule.get("log_redaction_required") is not True:
            violations.append(
                DataClassificationContractViolation(
                    reason="sensitive_log_redaction_required",
                    details=(
                        f"`{sensitivity}` mapped class `{taxonomy_id}` must enforce "
                        "log_redaction_required=true."
                    ),
                )
            )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_references",
                details="references must be a non-empty object.",
            )
        )
    else:
        for key, value in references.items():
            if not isinstance(value, str) or not value.startswith("docs/"):
                violations.append(
                    DataClassificationContractViolation(
                        reason="invalid_reference_path",
                        details=f"references.{key} must be a docs/* path.",
                    )
                )
                continue
            ref_path = REPO_ROOT / value
            if not ref_path.exists():
                violations.append(
                    DataClassificationContractViolation(
                        reason="missing_reference_file",
                        details=f"reference file not found: {value}",
                    )
                )

    entries = inventory.get("entries")
    if not isinstance(entries, list):
        violations.append(
            DataClassificationContractViolation(
                reason="invalid_inventory_entries",
                details="api-inventory entries must be a list.",
            )
        )
        entries = []

    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        data_sensitivity = entry.get("data_sensitivity")
        if not isinstance(data_sensitivity, str):
            violations.append(
                DataClassificationContractViolation(
                    reason="invalid_inventory_data_sensitivity",
                    details=f"entries[{index}].data_sensitivity must be a string.",
                )
            )
            continue
        mapped = mapping.get(data_sensitivity)
        if mapped is None:
            violations.append(
                DataClassificationContractViolation(
                    reason="inventory_sensitivity_unmapped",
                    details=(
                        f"entries[{index}] data_sensitivity `{data_sensitivity}` is not mapped "
                        "by classification policy."
                    ),
                )
            )

    return violations


def run_policy_check() -> int:
    violations = collect_data_classification_contract_violations()
    if not violations:
        print("[data-classification-contract] ok: data classification contract satisfied")
        return 0

    print("[data-classification-contract] failed:", file=sys.stderr)
    for item in violations:
        print(f"  - reason={item.reason} details={item.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
