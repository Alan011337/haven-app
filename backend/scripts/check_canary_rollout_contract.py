#!/usr/bin/env python3
"""REL-GATE-02: Validate canary rollout hooks contract.

Checks:
1. Canary guard workflow exists
2. Canary guard script exists with rollback capability
3. Prompt rollout policy references canary strategy
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"

FAILURES: list[str] = []


def _check_canary_guard_workflow() -> None:
    wf = REPO_ROOT / ".github" / "workflows" / "canary-guard.yml"
    if not wf.exists():
        FAILURES.append("canary-guard.yml workflow not found")


def _check_canary_guard_script() -> None:
    script = BACKEND_ROOT / "scripts" / "run_canary_guard.py"
    if not script.exists():
        FAILURES.append("run_canary_guard.py script not found")
        return
    source = script.read_text()
    if "rollback" not in source.lower():
        FAILURES.append("run_canary_guard.py missing rollback capability")


def _check_prompt_rollout_policy() -> None:
    policy_path = REPO_ROOT / "docs" / "security" / "prompt-rollout-policy.json"
    if not policy_path.exists():
        FAILURES.append("prompt-rollout-policy.json not found")
        return
    try:
        data = json.loads(policy_path.read_text())
    except json.JSONDecodeError:
        FAILURES.append("prompt-rollout-policy.json is invalid JSON")
        return
    strategy = data.get("canary_strategy", {})
    if not strategy.get("mode"):
        FAILURES.append("prompt-rollout-policy.json missing canary_strategy.mode")


def main() -> int:
    _check_canary_guard_workflow()
    _check_canary_guard_script()
    _check_prompt_rollout_policy()

    if FAILURES:
        print("REL-GATE-02 canary rollout contract FAILED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print("REL-GATE-02 canary rollout contract OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
