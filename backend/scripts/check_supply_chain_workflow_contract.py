#!/usr/bin/env python3
"""Validate supply-chain workflow baseline contract."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "supply-chain-security.yml"


def collect_violations() -> list[str]:
    if not WORKFLOW_PATH.exists():
        return ["missing_supply_chain_workflow"]

    text = WORKFLOW_PATH.read_text(encoding="utf-8")
    violations: list[str] = []
    required_markers = (
        "name: Supply Chain Security",
        "pull_request:",
        "push:",
        "schedule:",
        "concurrency:",
        "pip-audit -r backend/requirements.txt",
        "npm audit --omit=dev --audit-level=high",
        "gitleaks/gitleaks-action@v2",
        "continue-on-error: ${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name != github.repository }}",
    )
    for marker in required_markers:
        if marker not in text:
            violations.append(f"missing_marker:{marker}")
    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[supply-chain-workflow-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[supply-chain-workflow-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
