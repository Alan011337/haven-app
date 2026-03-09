#!/usr/bin/env python3
"""Policy-as-code gate for growth feature flag kill-switch coverage (META-05)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "growth-kill-switch-coverage.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "growth-kill-switch-coverage"

REQUIRED_CUJ_FLAGS = (
    "growth_referral_enabled",
    "growth_ab_experiment_enabled",
    "growth_pricing_experiment_enabled",
    "growth_reengagement_hooks_enabled",
)

REQUIRED_REFERENCES = (
    "feature_flag_service",
    "audit_doc",
    "execution_plan",
)


@dataclass(frozen=True)
class GrowthKillSwitchCoverageViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _as_str(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def collect_growth_kill_switch_coverage_violations(
    *,
    payload: dict[str, Any] | None = None,
    feature_flags_module: Any | None = None,
) -> list[GrowthKillSwitchCoverageViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[GrowthKillSwitchCoverageViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            GrowthKillSwitchCoverageViolation(
                "invalid_schema_version",
                f"schema_version must be `{SCHEMA_VERSION}`.",
            )
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            GrowthKillSwitchCoverageViolation(
                "invalid_artifact_kind",
                f"artifact_kind must be `{ARTIFACT_KIND}`.",
            )
        )

    entries = policy.get("entries")
    if not isinstance(entries, list) or not entries:
        violations.append(
            GrowthKillSwitchCoverageViolation(
                "invalid_entries",
                "entries must be a non-empty list.",
            )
        )
        entries = []

    references = policy.get("references")
    if not isinstance(references, dict):
        violations.append(
            GrowthKillSwitchCoverageViolation(
                "invalid_references",
                "references must be an object.",
            )
        )
    else:
        for key in REQUIRED_REFERENCES:
            ref_path = _as_str(references.get(key))
            if not ref_path:
                violations.append(
                    GrowthKillSwitchCoverageViolation(
                        "missing_reference",
                        f"references.{key} must be non-empty path.",
                    )
                )
                continue
            if not (REPO_ROOT / ref_path).exists():
                violations.append(
                    GrowthKillSwitchCoverageViolation(
                        "missing_reference_file",
                        f"references.{key} not found: {ref_path}",
                    )
                )

    flags_seen: set[str] = set()
    kill_switch_seen: set[str] = set()

    for idx, item in enumerate(entries):
        if not isinstance(item, dict):
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "invalid_entry",
                    f"entries[{idx}] must be object.",
                )
            )
            continue

        flag_name = _as_str(item.get("flag"))
        kill_switch = _as_str(item.get("kill_switch"))
        rollback_command = _as_str(item.get("rollback_command"))
        risk_tier = _as_str(item.get("risk_tier"))
        cuj_impact = item.get("cuj_impact")

        if not flag_name:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "missing_flag",
                    f"entries[{idx}].flag must be non-empty string.",
                )
            )
        else:
            flags_seen.add(flag_name)

        if not kill_switch:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "missing_kill_switch",
                    f"entries[{idx}].kill_switch must be non-empty string.",
                )
            )
        else:
            kill_switch_seen.add(kill_switch)

        if not rollback_command:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "missing_rollback_command",
                    f"entries[{idx}].rollback_command must be non-empty string.",
                )
            )

        if risk_tier not in {"tier_0", "tier_1", "tier_2"}:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "invalid_risk_tier",
                    f"entries[{idx}].risk_tier must be tier_0|tier_1|tier_2.",
                )
            )

        if not isinstance(cuj_impact, bool):
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "invalid_cuj_impact",
                    f"entries[{idx}].cuj_impact must be boolean.",
                )
            )

    for required in REQUIRED_CUJ_FLAGS:
        if required not in flags_seen:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "missing_required_cuj_flag",
                    f"required CUJ growth flag missing from policy entries: {required}",
                )
            )

    if feature_flags_module is None:
        from app.services import feature_flags as feature_flags_module  # noqa: PLC0415

    default_flags = getattr(feature_flags_module, "DEFAULT_FEATURE_FLAGS", {})
    default_kill_switches = getattr(feature_flags_module, "DEFAULT_KILL_SWITCHES", {})
    kill_switch_to_flag = getattr(feature_flags_module, "KILL_SWITCH_TO_FLAG", {})

    if not isinstance(default_flags, dict) or not isinstance(default_kill_switches, dict) or not isinstance(
        kill_switch_to_flag, dict
    ):
        violations.append(
            GrowthKillSwitchCoverageViolation(
                "invalid_feature_flag_runtime",
                "feature flag runtime maps are missing or invalid.",
            )
        )
        return violations

    for flag_name in sorted(flags_seen):
        if flag_name not in default_flags:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "flag_missing_in_runtime",
                    f"flag not found in DEFAULT_FEATURE_FLAGS: {flag_name}",
                )
            )

    for kill_switch in sorted(kill_switch_seen):
        if kill_switch not in default_kill_switches:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "kill_switch_missing_in_runtime",
                    f"kill switch not found in DEFAULT_KILL_SWITCHES: {kill_switch}",
                )
            )

    for kill_switch in sorted(kill_switch_seen):
        mapped = _as_str(kill_switch_to_flag.get(kill_switch))
        if not mapped:
            violations.append(
                GrowthKillSwitchCoverageViolation(
                    "kill_switch_mapping_missing",
                    f"kill switch missing from KILL_SWITCH_TO_FLAG: {kill_switch}",
                )
            )

    return violations


def run_policy_check() -> int:
    violations = collect_growth_kill_switch_coverage_violations()
    if not violations:
        print("[growth-kill-switch-coverage-contract] ok: growth kill-switch coverage contract satisfied")
        return 0

    print("[growth-kill-switch-coverage-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
