#!/usr/bin/env python3
"""Policy-as-code gate for OWASP API Top 10 mapping artifacts."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

CANONICAL_PATH = REPO_ROOT / "docs" / "security" / "owasp-api-top10-mapping.md"
ALIAS_PATH = REPO_ROOT / "docs" / "security" / "owasp_api_top10_mapping.md"
SECURITY_GATE_PATH = BACKEND_ROOT / "scripts" / "security-gate.sh"
BOLA_MATRIX_TEST_PATH = BACKEND_ROOT / "tests" / "security" / "test_bola_matrix.py"
BOLA_SUBJECT_TEST_PATH = BACKEND_ROOT / "tests" / "security" / "test_bola_subject_matrix.py"


@dataclass(frozen=True)
class OwaspMappingViolation:
    reason: str
    details: str


def collect_owasp_mapping_contract_violations() -> list[OwaspMappingViolation]:
    violations: list[OwaspMappingViolation] = []

    if not CANONICAL_PATH.exists():
        violations.append(
            OwaspMappingViolation(
                "missing_canonical_mapping",
                f"Missing canonical mapping document: {CANONICAL_PATH}",
            )
        )
        return violations

    if not ALIAS_PATH.exists():
        violations.append(
            OwaspMappingViolation(
                "missing_alias_mapping",
                f"Missing checklist-compatible alias document: {ALIAS_PATH}",
            )
        )
    else:
        alias_text = ALIAS_PATH.read_text(encoding="utf-8")
        if "owasp-api-top10-mapping.md" not in alias_text:
            violations.append(
                OwaspMappingViolation(
                    "alias_missing_canonical_ref",
                    "Alias mapping must reference canonical mapping path.",
                )
            )

    canonical_text = CANONICAL_PATH.read_text(encoding="utf-8")
    required_fragments = (
        "OWASP API Security Top 10 (2023)",
        "API1: Broken Object Level Authorization (BOLA)",
        "backend/tests/security/test_bola_matrix.py",
        "backend/tests/security/test_bola_subject_matrix.py",
        "backend/scripts/security-gate.sh",
    )
    for fragment in required_fragments:
        if fragment not in canonical_text:
            violations.append(
                OwaspMappingViolation(
                    "missing_canonical_fragment",
                    f"Canonical mapping missing required fragment: {fragment}",
                )
            )

    if not SECURITY_GATE_PATH.exists():
        violations.append(
            OwaspMappingViolation(
                "missing_security_gate",
                f"Missing security gate script: {SECURITY_GATE_PATH}",
            )
        )
    else:
        gate_text = SECURITY_GATE_PATH.read_text(encoding="utf-8")
        for required in (
            "check_owasp_api_top10_mapping_contract.py",
            "tests/security/test_bola_matrix.py",
            "tests/security/test_bola_subject_matrix.py",
            "tests/test_owasp_api_top10_mapping_contract_policy.py",
        ):
            if required not in gate_text:
                violations.append(
                    OwaspMappingViolation(
                        "missing_security_gate_reference",
                        f"security-gate.sh missing required OWASP reference: {required}",
                    )
                )

    if not BOLA_MATRIX_TEST_PATH.exists():
        violations.append(
            OwaspMappingViolation(
                "missing_bola_matrix_test",
                f"Missing BOLA matrix test: {BOLA_MATRIX_TEST_PATH}",
            )
        )
    if not BOLA_SUBJECT_TEST_PATH.exists():
        violations.append(
            OwaspMappingViolation(
                "missing_bola_subject_test",
                f"Missing BOLA subject matrix test: {BOLA_SUBJECT_TEST_PATH}",
            )
        )

    return violations


def run_policy_check() -> int:
    violations = collect_owasp_mapping_contract_violations()
    if not violations:
        print("[owasp-api-top10-mapping-contract] ok: mapping contract satisfied")
        return 0
    print("[owasp-api-top10-mapping-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(
            f"  - reason={violation.reason} details={violation.details}",
            file=sys.stderr,
        )
    return 1


def main() -> int:
    return run_policy_check()


if __name__ == "__main__":
    raise SystemExit(main())
