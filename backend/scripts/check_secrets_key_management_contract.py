#!/usr/bin/env python3
"""Policy-as-code gate for secrets/key management (P0 SEC-05)."""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "secrets-key-management-policy.json"
CHECK_ENV_PATH = BACKEND_ROOT / "scripts" / "check_env.py"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "secrets-key-management-policy"


@dataclass(frozen=True)
class SecretsContractViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_required_keys_from_check_env() -> set[str]:
    source = CHECK_ENV_PATH.read_text(encoding="utf-8")
    match = re.search(r"REQUIRED_KEYS\s*=\s*\((?P<body>.*?)\)", source, flags=re.DOTALL)
    if not match:
        return set()
    body = match.group("body")
    keys = set(re.findall(r'"([A-Z0-9_]+)"', body))
    return keys


def collect_secrets_key_management_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[SecretsContractViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[SecretsContractViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            SecretsContractViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            SecretsContractViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    env_sep = policy.get("environment_separation")
    if not isinstance(env_sep, dict):
        violations.append(SecretsContractViolation("invalid_environment_separation", "must be object"))
    else:
        dev_env = env_sep.get("dev_env_file_path")
        if not isinstance(dev_env, str) or not dev_env.strip():
            violations.append(
                SecretsContractViolation("invalid_dev_env_file_path", "environment_separation.dev_env_file_path required")
            )
        if env_sep.get("prod_secret_manager_required") is not True:
            violations.append(
                SecretsContractViolation(
                    "invalid_prod_secret_manager_requirement",
                    "environment_separation.prod_secret_manager_required must be true",
                )
            )
        prohibited = env_sep.get("prohibited_repo_files")
        if not isinstance(prohibited, list) or not prohibited:
            violations.append(
                SecretsContractViolation(
                    "invalid_prohibited_repo_files",
                    "environment_separation.prohibited_repo_files must be non-empty list",
                )
            )
        else:
            for rel in prohibited:
                if not isinstance(rel, str) or not rel.strip():
                    violations.append(
                        SecretsContractViolation("invalid_prohibited_repo_file_path", "all prohibited paths must be strings")
                    )
                    continue
                if (REPO_ROOT / rel).exists():
                    violations.append(
                        SecretsContractViolation("prohibited_secret_file_present", f"prohibited repo file exists: {rel}")
                    )

    key_groups = policy.get("key_groups")
    if not isinstance(key_groups, dict) or not key_groups:
        violations.append(SecretsContractViolation("invalid_key_groups", "key_groups must be non-empty object"))
    else:
        required_group = key_groups.get("backend_required")
        if not isinstance(required_group, list) or not required_group:
            violations.append(
                SecretsContractViolation("invalid_backend_required_group", "key_groups.backend_required required")
            )
        else:
            required_set = {k for k in required_group if isinstance(k, str)}
            expected_from_check_env = _extract_required_keys_from_check_env()
            missing_from_policy = sorted(expected_from_check_env - required_set)
            if missing_from_policy:
                violations.append(
                    SecretsContractViolation(
                        "missing_backend_required_keys",
                        f"backend_required missing check_env REQUIRED_KEYS: {', '.join(missing_from_policy)}",
                    )
                )
        for name, keys in key_groups.items():
            if not isinstance(keys, list) or not keys:
                violations.append(
                    SecretsContractViolation("invalid_key_group", f"key_groups.{name} must be non-empty list")
                )
                continue
            for key in keys:
                if not isinstance(key, str) or not re.fullmatch(r"[A-Z0-9_]+", key):
                    violations.append(
                        SecretsContractViolation(
                            "invalid_key_name",
                            f"key_groups.{name} contains invalid key name `{key}`",
                        )
                    )

    rotation = policy.get("rotation_policy_days")
    if not isinstance(rotation, dict) or not rotation:
        violations.append(
            SecretsContractViolation("invalid_rotation_policy_days", "rotation_policy_days must be non-empty object")
        )
    else:
        for group_name, days in rotation.items():
            if not isinstance(days, int) or days <= 0:
                violations.append(
                    SecretsContractViolation(
                        "invalid_rotation_days_value",
                        f"rotation_policy_days.{group_name} must be positive integer",
                    )
                )
                continue
            if days > 180:
                violations.append(
                    SecretsContractViolation(
                        "rotation_days_too_long",
                        f"rotation_policy_days.{group_name} must be <= 180 days",
                    )
                )

    incident = policy.get("incident_response")
    if not isinstance(incident, dict):
        violations.append(SecretsContractViolation("invalid_incident_response", "incident_response must be object"))
    else:
        if incident.get("revoke_on_leak") is not True:
            violations.append(
                SecretsContractViolation("invalid_revoke_on_leak", "incident_response.revoke_on_leak must be true")
            )
        if incident.get("require_postmortem") is not True:
            violations.append(
                SecretsContractViolation(
                    "invalid_require_postmortem", "incident_response.require_postmortem must be true"
                )
            )
        max_initial = incident.get("max_initial_response_minutes")
        if not isinstance(max_initial, int) or max_initial <= 0 or max_initial > 60:
            violations.append(
                SecretsContractViolation(
                    "invalid_max_initial_response_minutes",
                    "incident_response.max_initial_response_minutes must be 1..60",
                )
            )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(SecretsContractViolation("invalid_references", "references must be non-empty object"))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(SecretsContractViolation("invalid_reference_path", f"references.{key} must be path"))
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    SecretsContractViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_secrets_key_management_contract_violations()
    if not violations:
        print("[secrets-key-management-contract] ok: secrets/key policy contract satisfied")
        return 0
    print("[secrets-key-management-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
