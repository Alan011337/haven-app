#!/usr/bin/env python3
"""Policy-as-code gate for Safety UI Policy v1."""

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

POLICY_PATH = REPO_ROOT / "docs" / "safety" / "safety-ui-policy-v1.json"
SAFETY_POLICY_TS = REPO_ROOT / "frontend" / "src" / "lib" / "safety-policy.ts"
SAFETY_GATE_TSX = REPO_ROOT / "frontend" / "src" / "components" / "features" / "SafetyTierGate.tsx"
FORCE_LOCK_TSX = REPO_ROOT / "frontend" / "src" / "components" / "features" / "ForceLockBanner.tsx"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "safety-ui-policy"


@dataclass(frozen=True)
class SafetyUiPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_safety_ui_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[SafetyUiPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[SafetyUiPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            SafetyUiPolicyViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            SafetyUiPolicyViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    tiers = policy.get("tiers")
    if not isinstance(tiers, dict):
        violations.append(SafetyUiPolicyViolation("invalid_tiers", "tiers must be object."))
    else:
        required_tiers = ("0", "1", "2", "3")
        required_behavior = {
            "0": "normal",
            "1": "nudge",
            "2": "hide_with_cooldown",
            "3": "force_lock",
        }
        for tier in required_tiers:
            entry = tiers.get(tier)
            if not isinstance(entry, dict):
                violations.append(SafetyUiPolicyViolation("missing_tier", f"tiers.{tier} must be object."))
                continue
            if entry.get("partner_journal_behavior") != required_behavior[tier]:
                violations.append(
                    SafetyUiPolicyViolation(
                        "invalid_tier_behavior",
                        f"tiers.{tier}.partner_journal_behavior must be `{required_behavior[tier]}`.",
                    )
                )
            if not isinstance(entry.get("show_crisis_resources"), bool):
                violations.append(
                    SafetyUiPolicyViolation(
                        "invalid_show_crisis_resources",
                        f"tiers.{tier}.show_crisis_resources must be boolean.",
                    )
                )
            force_lock_seconds = entry.get("force_lock_seconds")
            if not isinstance(force_lock_seconds, int) or force_lock_seconds < 0:
                violations.append(
                    SafetyUiPolicyViolation(
                        "invalid_force_lock_seconds",
                        f"tiers.{tier}.force_lock_seconds must be non-negative integer.",
                    )
                )
        tier3 = tiers.get("3")
        if isinstance(tier3, dict) and tier3.get("force_lock_seconds") != 30:
            violations.append(
                SafetyUiPolicyViolation("invalid_tier3_force_lock_seconds", "tiers.3.force_lock_seconds must be 30.")
            )

    resources = policy.get("crisis_resources")
    if not isinstance(resources, list) or len(resources) < 2:
        violations.append(SafetyUiPolicyViolation("invalid_crisis_resources", "crisis_resources must have >=2 items."))
    else:
        numbers = {str(item.get("number")) for item in resources if isinstance(item, dict)}
        for required_number in ("1925", "113"):
            if required_number not in numbers:
                violations.append(
                    SafetyUiPolicyViolation(
                        "missing_crisis_number", f"crisis_resources must include number `{required_number}`."
                    )
                )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(SafetyUiPolicyViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(SafetyUiPolicyViolation("invalid_reference_path", f"references.{key} must be path."))
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    SafetyUiPolicyViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    # Runtime alignment checks against frontend implementation.
    policy_text = _read_text(SAFETY_POLICY_TS)
    gate_text = _read_text(SAFETY_GATE_TSX)
    lock_text = _read_text(FORCE_LOCK_TSX)

    for marker in ("partnerJournalBehavior: 'normal'", "partnerJournalBehavior: 'nudge'"):
        if marker not in policy_text:
            violations.append(SafetyUiPolicyViolation("missing_safety_policy_marker", f"missing marker: {marker}"))
    if "partnerJournalBehavior: 'hide_with_cooldown'" not in policy_text:
        violations.append(
            SafetyUiPolicyViolation("missing_safety_policy_marker", "missing hide_with_cooldown behavior in policy.")
        )
    if "partnerJournalBehavior: 'force_lock'" not in policy_text:
        violations.append(SafetyUiPolicyViolation("missing_safety_policy_marker", "missing force_lock behavior in policy."))

    if "cooldownSeconds={30}" not in gate_text:
        violations.append(
            SafetyUiPolicyViolation("missing_force_lock_cooldown_wiring", "SafetyTierGate must pass cooldownSeconds=30.")
        )
    if "CRISIS_HOTLINES" not in gate_text or "CRISIS_HOTLINES" not in lock_text:
        violations.append(
            SafetyUiPolicyViolation(
                "missing_crisis_hotline_wiring",
                "SafetyTierGate and ForceLockBanner must use CRISIS_HOTLINES.",
            )
        )

    if not re.search(r"cooldownSeconds\s*=\s*30", lock_text):
        violations.append(
            SafetyUiPolicyViolation("invalid_force_lock_default", "ForceLockBanner cooldownSeconds default must be 30.")
        )

    return violations


def run_policy_check() -> int:
    violations = collect_safety_ui_policy_contract_violations()
    if not violations:
        print("[safety-ui-policy-contract] ok: safety ui policy contract satisfied")
        return 0
    print("[safety-ui-policy-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
