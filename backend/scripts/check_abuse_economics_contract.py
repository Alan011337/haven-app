#!/usr/bin/env python3
"""Policy-as-code gate for abuse economics policy contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

POLICY_PATH = REPO_ROOT / "docs" / "security" / "abuse-economics-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "abuse-economics-policy"


@dataclass(frozen=True)
class AbuseEconomicsViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _is_positive_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and value > 0


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and value > 0


def collect_abuse_economics_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[AbuseEconomicsViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[AbuseEconomicsViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            AbuseEconomicsViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            AbuseEconomicsViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    vectors = policy.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        violations.append(AbuseEconomicsViolation("invalid_vectors", "vectors must be a non-empty list."))
        vectors = []

    for idx, vector in enumerate(vectors):
        if not isinstance(vector, dict):
            violations.append(AbuseEconomicsViolation("invalid_vector_entry", f"vectors[{idx}] must be object."))
            continue
        for key in ("id", "description"):
            if not str(vector.get(key, "")).strip():
                violations.append(
                    AbuseEconomicsViolation("missing_vector_field", f"vectors[{idx}].{key} must be non-empty.")
                )
        if not _is_positive_number(vector.get("unit_cost_usd")):
            violations.append(
                AbuseEconomicsViolation("invalid_unit_cost", f"vectors[{idx}].unit_cost_usd must be > 0.")
            )
        for key in ("max_events_per_user_per_day", "max_events_per_ip_per_day"):
            if not _is_positive_int(vector.get(key)):
                violations.append(
                    AbuseEconomicsViolation("invalid_event_cap", f"vectors[{idx}].{key} must be positive int.")
                )
        controls = vector.get("mapped_controls")
        if not isinstance(controls, list) or not controls:
            violations.append(
                AbuseEconomicsViolation("missing_mapped_controls", f"vectors[{idx}].mapped_controls required.")
            )
            continue
        for control_ref in controls:
            if not isinstance(control_ref, str) or not control_ref.strip():
                violations.append(
                    AbuseEconomicsViolation("invalid_control_reference", f"vectors[{idx}] has invalid mapped control.")
                )
                continue
            if not (REPO_ROOT / control_ref).exists():
                violations.append(
                    AbuseEconomicsViolation(
                        "missing_control_reference_file",
                        f"vectors[{idx}] mapped control file not found: {control_ref}",
                    )
                )

    thresholds = policy.get("escalation_thresholds")
    if not isinstance(thresholds, dict):
        violations.append(
            AbuseEconomicsViolation("invalid_escalation_thresholds", "escalation_thresholds must be object.")
        )
    else:
        warn = thresholds.get("warn_daily_total_usd")
        block = thresholds.get("block_daily_total_usd")
        if not _is_positive_number(warn):
            violations.append(
                AbuseEconomicsViolation("invalid_warn_threshold", "warn_daily_total_usd must be > 0.")
            )
        if not _is_positive_number(block):
            violations.append(
                AbuseEconomicsViolation("invalid_block_threshold", "block_daily_total_usd must be > 0.")
            )
        if _is_positive_number(warn) and _is_positive_number(block) and warn >= block:
            violations.append(
                AbuseEconomicsViolation("invalid_threshold_order", "warn_daily_total_usd must be < block_daily_total_usd.")
            )

    references = policy.get("references")
    if not isinstance(references, dict) or not references:
        violations.append(AbuseEconomicsViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in references.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    AbuseEconomicsViolation("invalid_reference_path", f"references.{key} must be path string.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    AbuseEconomicsViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_abuse_economics_contract_violations()
    if not violations:
        print("[abuse-economics-contract] ok: abuse economics policy contract satisfied")
        return 0
    print("[abuse-economics-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
