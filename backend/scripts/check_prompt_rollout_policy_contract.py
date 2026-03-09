#!/usr/bin/env python3
"""Policy-as-code gate for prompt rollout policy contract."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent
POLICY_PATH = REPO_ROOT / "docs" / "security" / "prompt-rollout-policy.json"
SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt-rollout-policy"


@dataclass(frozen=True)
class PromptRolloutPolicyViolation:
    reason: str
    details: str


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def collect_prompt_rollout_policy_contract_violations(
    *, payload: dict[str, Any] | None = None
) -> list[PromptRolloutPolicyViolation]:
    policy = payload if payload is not None else _load_json(POLICY_PATH)
    violations: list[PromptRolloutPolicyViolation] = []

    if policy.get("schema_version") != SCHEMA_VERSION:
        violations.append(
            PromptRolloutPolicyViolation("invalid_schema_version", f"schema_version must be `{SCHEMA_VERSION}`.")
        )
    if policy.get("artifact_kind") != ARTIFACT_KIND:
        violations.append(
            PromptRolloutPolicyViolation("invalid_artifact_kind", f"artifact_kind must be `{ARTIFACT_KIND}`.")
        )

    strategy = policy.get("strategy")
    if not isinstance(strategy, dict):
        violations.append(PromptRolloutPolicyViolation("invalid_strategy", "strategy must be object."))
    else:
        if strategy.get("mode") != "canary_then_full_rollout":
            violations.append(
                PromptRolloutPolicyViolation("invalid_strategy_mode", "strategy.mode must be canary_then_full_rollout.")
            )
        canary_percent = strategy.get("canary_percent")
        if not isinstance(canary_percent, int) or not (1 <= canary_percent <= 50):
            violations.append(
                PromptRolloutPolicyViolation("invalid_canary_percent", "canary_percent must be int between 1 and 50.")
            )
        gate = strategy.get("promotion_gate")
        if not isinstance(gate, dict):
            violations.append(
                PromptRolloutPolicyViolation("invalid_promotion_gate", "strategy.promotion_gate must be object.")
            )
        else:
            for key in ("health_slo_required", "safety_regression_required"):
                if gate.get(key) is not True:
                    violations.append(
                        PromptRolloutPolicyViolation("missing_promotion_requirement", f"promotion_gate.{key} must be true.")
                    )
            max_burn = gate.get("max_allowed_burn_rate")
            if not isinstance(max_burn, (int, float)) or max_burn <= 0:
                violations.append(
                    PromptRolloutPolicyViolation("invalid_max_allowed_burn_rate", "max_allowed_burn_rate must be > 0.")
                )

    guardrails = policy.get("guardrails")
    if not isinstance(guardrails, dict):
        violations.append(PromptRolloutPolicyViolation("invalid_guardrails", "guardrails must be object."))
    else:
        for key in (
            "rollback_on_slo_degrade",
            "rollback_on_safety_regression",
            "rollback_on_prompt_abuse_spike",
        ):
            if guardrails.get(key) is not True:
                violations.append(
                    PromptRolloutPolicyViolation("missing_guardrail", f"guardrails.{key} must be true.")
                )

    refs = policy.get("references")
    if not isinstance(refs, dict) or not refs:
        violations.append(PromptRolloutPolicyViolation("invalid_references", "references must be non-empty object."))
    else:
        for key, rel_path in refs.items():
            if not isinstance(rel_path, str) or not rel_path.strip():
                violations.append(
                    PromptRolloutPolicyViolation("invalid_reference_path", f"references.{key} must be path.")
                )
                continue
            if not (REPO_ROOT / rel_path).exists():
                violations.append(
                    PromptRolloutPolicyViolation("missing_reference_file", f"references.{key} not found: {rel_path}")
                )

    return violations


def run_policy_check() -> int:
    violations = collect_prompt_rollout_policy_contract_violations()
    if not violations:
        print("[prompt-rollout-policy-contract] ok: prompt rollout policy contract satisfied")
        return 0
    print("[prompt-rollout-policy-contract] failed:", file=sys.stderr)
    for v in violations:
        print(f"  - reason={v.reason} details={v.details}", file=sys.stderr)
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
