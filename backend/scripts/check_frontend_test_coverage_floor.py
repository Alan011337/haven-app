#!/usr/bin/env python3
"""Guardrail: keep a minimum frontend E2E and contract test baseline."""

from __future__ import annotations

from pathlib import Path
import re


REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_E2E_DIR = REPO_ROOT / "frontend" / "e2e"
FRONTEND_UNIT_LIB_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "__tests__"
FRONTEND_UNIT_HOOKS_DIR = REPO_ROOT / "frontend" / "src" / "hooks" / "__tests__"
FRONTEND_PACKAGE_JSON = REPO_ROOT / "frontend" / "package.json"
BACKEND_TESTS_DIR = REPO_ROOT / "backend" / "tests"
MIN_E2E_TEST_BLOCKS = 12
MIN_UNIT_TEST_FILES = 4
MIN_HOOKS_UNIT_TEST_FILES = 1
REQUIRED_CONTRACT_TESTS = {
    "test_frontend_api_transport_contract.py",
    "test_frontend_polling_governance_contract.py",
}


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not FRONTEND_E2E_DIR.exists():
        violations.append("missing_frontend_e2e_dir")
    else:
        blocks = 0
        for path in FRONTEND_E2E_DIR.rglob("*.spec.ts"):
            text = path.read_text(encoding="utf-8")
            blocks += len(re.findall(r"\btest\s*\(", text))
        if blocks < MIN_E2E_TEST_BLOCKS:
            violations.append(f"frontend_e2e_below_floor:{blocks}<{MIN_E2E_TEST_BLOCKS}")

    unit_test_total = 0
    hooks_unit_total = 0
    if not FRONTEND_UNIT_LIB_DIR.exists():
        violations.append("missing_frontend_lib_unit_test_dir")
    else:
        unit_test_total += len(list(FRONTEND_UNIT_LIB_DIR.glob("*.test.ts")))
    if not FRONTEND_UNIT_HOOKS_DIR.exists():
        violations.append("missing_frontend_hooks_unit_test_dir")
    else:
        hooks_unit_total = len(list(FRONTEND_UNIT_HOOKS_DIR.glob("*.test.ts")))
        unit_test_total += hooks_unit_total

    if unit_test_total < MIN_UNIT_TEST_FILES:
        violations.append(
            f"frontend_unit_tests_below_floor:{unit_test_total}<{MIN_UNIT_TEST_FILES}"
        )
    if hooks_unit_total < MIN_HOOKS_UNIT_TEST_FILES:
        violations.append(
            f"frontend_hooks_unit_tests_below_floor:{hooks_unit_total}<{MIN_HOOKS_UNIT_TEST_FILES}"
        )

    if not FRONTEND_PACKAGE_JSON.exists():
        violations.append("missing_frontend_package_json")
    else:
        package_text = FRONTEND_PACKAGE_JSON.read_text(encoding="utf-8")
        if '"test:unit"' not in package_text:
            violations.append("missing_frontend_test_unit_script")

    if not BACKEND_TESTS_DIR.exists():
        violations.append("missing_backend_tests_dir")
    else:
        existing = {p.name for p in BACKEND_TESTS_DIR.glob("test_*.py")}
        for required in REQUIRED_CONTRACT_TESTS:
            if required not in existing:
                violations.append(f"missing_contract_test:{required}")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[frontend-test-coverage-floor] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[frontend-test-coverage-floor] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
