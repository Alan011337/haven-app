#!/usr/bin/env python3
"""Policy-as-code gate for consent receipt baseline."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "consent-receipt-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "consent-receipt-policy"


@dataclass(frozen=True)
class ConsentReceiptViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_consent_receipt_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[ConsentReceiptViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[ConsentReceiptViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            ConsentReceiptViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            ConsentReceiptViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    events = policy.get("consent_events")
    if not isinstance(events, list) or not events:
        violations.append(ConsentReceiptViolation("invalid_consent_events", "consent_events must be non-empty list."))
        events = []
    for idx, event in enumerate(events):
        if not isinstance(event, dict):
            violations.append(
                ConsentReceiptViolation("invalid_consent_event_entry", f"consent_events[{idx}] must be object.")
            )
            continue
        for key in ("id", "description", "evidence_path"):
            if not str(event.get(key, "")).strip():
                violations.append(
                    ConsentReceiptViolation("missing_consent_event_field", f"consent_events[{idx}].{key} required.")
                )
        required_fields = event.get("required_fields")
        if not isinstance(required_fields, list) or not required_fields:
            violations.append(
                ConsentReceiptViolation(
                    "invalid_required_fields",
                    f"consent_events[{idx}].required_fields must be non-empty list.",
                )
            )
        evidence_path = event.get("evidence_path")
        if isinstance(evidence_path, str) and evidence_path.strip():
            if not (REPO_ROOT / evidence_path).exists():
                violations.append(
                    ConsentReceiptViolation(
                        "missing_evidence_path_file",
                        f"consent_events[{idx}].evidence_path not found: {evidence_path}",
                    )
                )

    versions = policy.get("policy_versions")
    if not isinstance(versions, dict):
        violations.append(ConsentReceiptViolation("invalid_policy_versions", "policy_versions must be object."))
    else:
        for key in ("terms_version", "privacy_version"):
            value = versions.get(key)
            if not isinstance(value, str) or not value.startswith("v"):
                violations.append(
                    ConsentReceiptViolation("invalid_policy_version", f"policy_versions.{key} must start with `v`.")
                )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(ConsentReceiptViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    ConsentReceiptViolation("invalid_reference_path", f"references.{key} must be path string.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    ConsentReceiptViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_consent_receipt_contract_violations()
    if not violations:
        print("[consent-receipt-contract] ok: consent receipt contract satisfied")
        return 0
    print("[consent-receipt-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
