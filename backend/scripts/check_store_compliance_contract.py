#!/usr/bin/env python3
"""Policy-as-code gate for app store compliance matrix."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "store-compliance-matrix.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "store-compliance-matrix"
REQUIRED_PLATFORMS = ("ios_app_store", "google_play")
REQUIRED_PLATFORM_FIELDS = (
    "age_rating",
    "privacy_policy_url",
    "terms_url",
    "data_deletion_url",
    "contact_email",
    "ai_disclosure",
)
REQUIRED_REFERENCE_KEYS = (
    "privacy_policy",
    "terms_of_service",
    "data_rights",
    "ai_policy",
    "entitlement_parity_test",
)


@dataclass(frozen=True)
class StoreComplianceViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_store_compliance_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[StoreComplianceViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[StoreComplianceViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            StoreComplianceViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            StoreComplianceViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    platforms = policy.get("platforms")
    if not isinstance(platforms, dict):
        violations.append(StoreComplianceViolation("invalid_platforms", "platforms must be object."))
    else:
        for platform in REQUIRED_PLATFORMS:
            entry = platforms.get(platform)
            if not isinstance(entry, dict):
                violations.append(
                    StoreComplianceViolation("missing_platform_entry", f"platforms.{platform} must be object.")
                )
                continue
            for field in REQUIRED_PLATFORM_FIELDS:
                value = entry.get(field)
                if field == "ai_disclosure":
                    if value is not True:
                        violations.append(
                            StoreComplianceViolation(
                                "invalid_ai_disclosure",
                                f"platforms.{platform}.ai_disclosure must be true.",
                            )
                        )
                    continue
                if not isinstance(value, str) or not value.strip():
                    violations.append(
                        StoreComplianceViolation(
                            "missing_platform_field",
                            f"platforms.{platform}.{field} must be non-empty string.",
                        )
                    )
            if isinstance(entry.get("age_rating"), str) and entry["age_rating"].strip() != "18+":
                violations.append(
                    StoreComplianceViolation(
                        "invalid_age_rating",
                        f"platforms.{platform}.age_rating must be `18+`.",
                    )
                )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(StoreComplianceViolation("invalid_references", "references must be non-empty object."))
    else:
        for required_key in REQUIRED_REFERENCE_KEYS:
            if required_key not in refs:
                violations.append(
                    StoreComplianceViolation(
                        "missing_reference_key",
                        f"references.{required_key} is required.",
                    )
                )
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    StoreComplianceViolation("invalid_reference_path", f"references.{key} must be path.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    StoreComplianceViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_store_compliance_contract_violations()
    if not violations:
        print("[store-compliance-contract] ok: store compliance matrix contract satisfied")
        return 0
    print("[store-compliance-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
