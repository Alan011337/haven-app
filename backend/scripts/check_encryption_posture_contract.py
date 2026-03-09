#!/usr/bin/env python3
"""Policy-as-code gate for encryption posture baseline."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "encryption-posture-policy.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "encryption-posture-policy"


@dataclass(frozen=True)
class EncryptionPostureViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_encryption_posture_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[EncryptionPostureViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[EncryptionPostureViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            EncryptionPostureViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            EncryptionPostureViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    transport = policy.get("transport_security")
    if not isinstance(transport, dict):
        violations.append(
            EncryptionPostureViolation("invalid_transport_security", "transport_security must be object.")
        )
    else:
        for key in ("tls_required", "hsts_required"):
            if transport.get(key) is not True:
                violations.append(
                    EncryptionPostureViolation("missing_transport_requirement", f"transport_security.{key} must be true.")
                )
        max_age = transport.get("hsts_min_max_age_seconds")
        if not isinstance(max_age, int) or max_age < 31536000:
            violations.append(
                EncryptionPostureViolation("invalid_hsts_min_age", "hsts_min_max_age_seconds must be >= 31536000.")
            )

    at_rest = policy.get("data_at_rest")
    if not isinstance(at_rest, dict):
        violations.append(EncryptionPostureViolation("invalid_data_at_rest", "data_at_rest must be object."))
    else:
        for key in (
            "database_encryption_required",
            "sensitive_field_log_redaction_required",
            "field_level_encryption_required",
        ):
            if at_rest.get(key) is not True:
                violations.append(
                    EncryptionPostureViolation("missing_at_rest_requirement", f"data_at_rest.{key} must be true.")
                )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(EncryptionPostureViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    EncryptionPostureViolation("invalid_reference_path", f"references.{key} must be path string.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    EncryptionPostureViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_encryption_posture_contract_violations()
    if not violations:
        print("[encryption-posture-contract] ok: encryption posture contract satisfied")
        return 0
    print("[encryption-posture-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
