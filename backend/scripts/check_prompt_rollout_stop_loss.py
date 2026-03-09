#!/usr/bin/env python3
"""AI-OPS-01: Validate prompt rollout policy has stop-loss guardrails wired.

Checks that the prompt-rollout-policy.json:
  - Has canary strategy with promotion gate
  - Has guardrails with rollback conditions
  - References canary_guard_script and canary_workflow
  - References safety tests

Also validates that the referenced files exist in the repo.

Exit 0 = pass, exit 1 = fail.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "prompt-rollout-policy.json"

REQUIRED_GUARDRAILS = [
    "rollback_on_slo_degrade",
    "rollback_on_safety_regression",
    "rollback_on_prompt_abuse_spike",
]

REQUIRED_REFERENCES = [
    "canary_guard_script",
    "canary_workflow",
    "safety_tests",
]

PROMOTION_GATE_FIELDS = [
    "health_slo_required",
    "safety_regression_required",
    "max_allowed_burn_rate",
]


def _load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.loads(fh.read())


def check_policy() -> list[str]:
    errors: list[str] = []

    if not POLICY_PATH.exists():
        return [f"missing policy file: {POLICY_PATH}"]

    policy = _load_json(POLICY_PATH)

    if policy.get("artifact_kind") != "prompt-rollout-policy":
        errors.append("artifact_kind must be 'prompt-rollout-policy'")

    strategy = policy.get("strategy", {})
    if strategy.get("mode") != "canary_then_full_rollout":
        errors.append("strategy.mode must be 'canary_then_full_rollout'")

    promotion_gate = strategy.get("promotion_gate", {})
    for field in PROMOTION_GATE_FIELDS:
        if field not in promotion_gate:
            errors.append(f"strategy.promotion_gate.{field} is required")

    burn_rate = promotion_gate.get("max_allowed_burn_rate")
    if burn_rate is not None and (not isinstance(burn_rate, (int, float)) or burn_rate <= 0):
        errors.append("max_allowed_burn_rate must be a positive number")

    guardrails = policy.get("guardrails", {})
    for key in REQUIRED_GUARDRAILS:
        if guardrails.get(key) is not True:
            errors.append(f"guardrails.{key} must be true (stop-loss required)")

    references = policy.get("references", {})
    for ref_key in REQUIRED_REFERENCES:
        ref_val = references.get(ref_key)
        if not ref_val:
            errors.append(f"references.{ref_key} is required")
            continue
        ref_path = REPO_ROOT / ref_val
        if not ref_path.exists():
            errors.append(f"referenced file not found: {ref_val}")

    return errors


def main() -> int:
    print("[prompt-rollout-stop-loss] checking prompt rollout policy guardrails...")

    errors = check_policy()
    if errors:
        for err in errors:
            print(f"  [FAIL] {err}")
        return 1

    print("  [PASS] policy has valid stop-loss guardrails")
    print("  [PASS] canary guard script and workflow referenced and exist")
    print("  [PASS] safety test references valid")
    print("[prompt-rollout-stop-loss] result: pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
