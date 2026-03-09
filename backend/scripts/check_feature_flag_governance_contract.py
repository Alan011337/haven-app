#!/usr/bin/env python3
"""Policy-as-code gate for runtime feature flag governance metadata."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "feature-flag-governance.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "feature-flag-governance"
ALLOWED_RISK_TIERS = {"tier_0", "tier_1", "tier_2"}


@dataclass(frozen=True)
class FeatureFlagGovernanceViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def collect_feature_flag_governance_violations(
    *,
    payload: dict[str, Any] | None = None,
    feature_flags_module: Any | None = None,
) -> list[FeatureFlagGovernanceViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[FeatureFlagGovernanceViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            FeatureFlagGovernanceViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            FeatureFlagGovernanceViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    references = policy.get("references")
    if not isinstance(references, dict):
        violations.append(
            FeatureFlagGovernanceViolation("invalid_references", "references must be an object.")
        )
    else:
        for key in ("feature_flag_service", "alpha_gate_doc", "release_checklist"):
            ref_path = _as_str(references.get(key))
            if not ref_path:
                violations.append(
                    FeatureFlagGovernanceViolation(
                        "missing_reference",
                        f"references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / ref_path).exists():
                violations.append(
                    FeatureFlagGovernanceViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {ref_path}",
                    )
                )

    entries = policy.get("entries")
    if not isinstance(entries, list) or not entries:
        violations.append(
            FeatureFlagGovernanceViolation(
                "invalid_entries",
                "entries must be a non-empty list.",
            )
        )
        entries = []

    if feature_flags_module is None:
        from app.services import feature_flags as feature_flags_module  # noqa: PLC0415

    default_flags = getattr(feature_flags_module, "DEFAULT_FEATURE_FLAGS", {})
    default_kill_switches = getattr(feature_flags_module, "DEFAULT_KILL_SWITCHES", {})
    kill_switch_to_flag = getattr(feature_flags_module, "KILL_SWITCH_TO_FLAG", {})

    if not isinstance(default_flags, dict) or not isinstance(default_kill_switches, dict):
        return [
            FeatureFlagGovernanceViolation(
                "invalid_feature_flag_runtime",
                "feature flag runtime maps are missing or invalid.",
            )
        ]

    seen_flags: set[str] = set()
    seen_kill_switches: set[str] = set()

    for idx, item in enumerate(entries):
        if not isinstance(item, dict):
            violations.append(
                FeatureFlagGovernanceViolation(
                    "invalid_entry",
                    f"entries[{idx}] must be object.",
                )
            )
            continue

        flag = _as_str(item.get("flag"))
        kill_switch = _as_str(item.get("kill_switch"))
        owner_team = _as_str(item.get("owner_team"))
        risk_tier = _as_str(item.get("risk_tier"))
        rollback_action = _as_str(item.get("rollback_action"))
        cuj_impact = item.get("cuj_impact")

        if not flag:
            violations.append(
                FeatureFlagGovernanceViolation("missing_flag", f"entries[{idx}].flag must be non-empty string.")
            )
        elif flag in seen_flags:
            violations.append(
                FeatureFlagGovernanceViolation("duplicate_flag_entry", f"duplicate flag entry: {flag}")
            )
        else:
            seen_flags.add(flag)

        if not kill_switch:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "missing_kill_switch",
                    f"entries[{idx}].kill_switch must be non-empty string.",
                )
            )
        elif kill_switch in seen_kill_switches:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "duplicate_kill_switch_entry",
                    f"duplicate kill switch entry: {kill_switch}",
                )
            )
        else:
            seen_kill_switches.add(kill_switch)

        if not owner_team:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "missing_owner_team",
                    f"entries[{idx}].owner_team must be non-empty string.",
                )
            )
        if risk_tier not in ALLOWED_RISK_TIERS:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "invalid_risk_tier",
                    f"entries[{idx}].risk_tier must be one of {sorted(ALLOWED_RISK_TIERS)}.",
                )
            )
        if not rollback_action:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "missing_rollback_action",
                    f"entries[{idx}].rollback_action must be non-empty string.",
                )
            )
        if not isinstance(cuj_impact, bool):
            violations.append(
                FeatureFlagGovernanceViolation(
                    "invalid_cuj_impact",
                    f"entries[{idx}].cuj_impact must be boolean.",
                )
            )

        if flag and flag not in default_flags:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "flag_missing_in_runtime",
                    f"flag not found in DEFAULT_FEATURE_FLAGS: {flag}",
                )
            )
        if kill_switch and kill_switch not in default_kill_switches:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "kill_switch_missing_in_runtime",
                    f"kill switch not found in DEFAULT_KILL_SWITCHES: {kill_switch}",
                )
            )
        if kill_switch and flag:
            mapped_flag = _as_str(kill_switch_to_flag.get(kill_switch))
            if mapped_flag != flag:
                violations.append(
                    FeatureFlagGovernanceViolation(
                        "kill_switch_mapping_mismatch",
                        f"kill switch `{kill_switch}` maps to `{mapped_flag}` (expected `{flag}`).",
                    )
                )

    for flag in sorted(default_flags.keys()):
        if flag not in seen_flags:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "missing_runtime_flag_entry",
                    f"policy missing runtime flag entry: {flag}",
                )
            )

    intentionally_unmapped = policy.get("intentionally_unmapped_kill_switches")
    if not isinstance(intentionally_unmapped, list):
        violations.append(
            FeatureFlagGovernanceViolation(
                "invalid_intentionally_unmapped",
                "intentionally_unmapped_kill_switches must be a list.",
            )
        )
        intentionally_unmapped = []
    intentionally_unmapped_set = {
        item.strip() for item in intentionally_unmapped if isinstance(item, str) and item.strip()
    }

    for kill_switch in sorted(default_kill_switches.keys()):
        mapped_flag = _as_str(kill_switch_to_flag.get(kill_switch))
        if mapped_flag:
            if kill_switch not in seen_kill_switches:
                violations.append(
                    FeatureFlagGovernanceViolation(
                        "missing_runtime_kill_switch_entry",
                        f"policy missing mapped kill switch entry: {kill_switch}",
                    )
                )
            continue
        if kill_switch not in intentionally_unmapped_set:
            violations.append(
                FeatureFlagGovernanceViolation(
                    "missing_unmapped_kill_switch_attestation",
                    f"unmapped runtime kill switch must be listed in intentionally_unmapped_kill_switches: {kill_switch}",
                )
            )

    return violations


def main() -> int:
    violations = collect_feature_flag_governance_violations()
    if not violations:
        print("[feature-flag-governance-contract] ok: runtime feature flag governance contract satisfied")
        return 0

    print("[feature-flag-governance-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
