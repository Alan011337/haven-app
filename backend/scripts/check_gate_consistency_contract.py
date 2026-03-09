#!/usr/bin/env python3
"""Fail-closed contract checks to keep release/security gate behavior aligned."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
SECURITY_GATE_PATH = BACKEND_ROOT / "scripts" / "security-gate.sh"
RELEASE_GATE_LOCAL_PATH = REPO_ROOT / "scripts" / "release-gate-local.sh"
GATE_COMMON_PATH = REPO_ROOT / "scripts" / "gate-common.sh"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def collect_contract_violations() -> list[str]:
    violations: list[str] = []
    if not GATE_COMMON_PATH.exists():
        violations.append("missing_shared_gate_helper:scripts/gate-common.sh")
        return violations

    security_text = _read(SECURITY_GATE_PATH)
    release_text = _read(RELEASE_GATE_LOCAL_PATH)

    if 'source "${SCRIPT_DIR}/gate-common.sh"' not in release_text:
        violations.append("release_gate_missing_shared_helper_source")
    if 'source "${BACKEND_DIR}/../scripts/gate-common.sh"' not in security_text:
        violations.append("security_gate_missing_shared_helper_source")

    required_release_markers = (
        "scripts/check_release_gate_override_contract.py",
        "SECURITY_GATE_PROFILE=",
        "API_INVENTORY_AUTO_WRITE",
        "scripts/check_api_contract_snapshot.py",
    )
    for marker in required_release_markers:
        if marker not in release_text:
            violations.append(f"release_gate_missing_marker:{marker}")

    required_security_markers = (
        "check_api_contract_snapshot.py",
        "check_event_tracking_privacy_contract.py",
        "check_feature_flag_governance_contract.py",
        "check_store_compliance_contract.py",
    )
    for marker in required_security_markers:
        if marker not in security_text:
            violations.append(f"security_gate_missing_marker:{marker}")

    return violations


def main() -> int:
    violations = collect_contract_violations()
    if violations:
        print("[gate-consistency-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[gate-consistency-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
