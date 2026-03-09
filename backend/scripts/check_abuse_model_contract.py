#!/usr/bin/env python3
"""Policy-as-code gate for abuse model policy."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "abuse-model-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "abuse-model-policy"
REQUIRED_SURFACES = ("api", "websocket", "ai_prompt")


@dataclass(frozen=True)
class AbuseModelViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_abuse_model_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AbuseModelViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AbuseModelViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(AbuseModelViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`."))
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(AbuseModelViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`."))

    surfaces = policy.get("surfaces")
    if not isinstance(surfaces, dict):
        violations.append(AbuseModelViolation("invalid_surfaces", "surfaces must be object."))
    else:
        for surface in REQUIRED_SURFACES:
            entry = surfaces.get(surface)
            if not isinstance(entry, dict):
                violations.append(AbuseModelViolation("missing_surface", f"surfaces.{surface} must be object."))
                continue
            for key in ("threats", "controls"):
                values = entry.get(key)
                if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
                    violations.append(
                        AbuseModelViolation("invalid_surface_entry", f"surfaces.{surface}.{key} must be non-empty string list.")
                    )

    playbook = policy.get("response_playbook")
    if not isinstance(playbook, dict):
        violations.append(AbuseModelViolation("invalid_response_playbook", "response_playbook must be object."))
    else:
        for key in ("requires_runbook", "requires_evidence"):
            if playbook.get(key) is not True:
                violations.append(AbuseModelViolation("missing_playbook_requirement", f"response_playbook.{key} must be true."))
        max_minutes = playbook.get("max_detection_to_mitigation_minutes")
        if not isinstance(max_minutes, int) or max_minutes <= 0:
            violations.append(
                AbuseModelViolation(
                    "invalid_response_sla",
                    "response_playbook.max_detection_to_mitigation_minutes must be positive int.",
                )
            )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(AbuseModelViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(AbuseModelViolation("invalid_reference_path", f"references.{key} must be path."))
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(AbuseModelViolation("missing_reference_file", f"references.{key} not found: {rel_path}"))
    return violations


def run_policy_check() -> int:
    violations = collect_abuse_model_contract_violations()
    if not violations:
        print("[abuse-model-contract] ok: abuse model policy contract satisfied")
        return 0
    print("[abuse-model-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
