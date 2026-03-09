#!/usr/bin/env python3
"""Validate env/secrets manifest stays aligned with frontend/backend env check scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = REPO_ROOT / "docs" / "ops" / "env-secrets-manifest.json"
BACKEND_ENV_CHECK_PATH = REPO_ROOT / "backend" / "scripts" / "check_env.py"
FRONTEND_ENV_CHECK_PATH = REPO_ROOT / "frontend" / "scripts" / "check-env.mjs"


def _extract_backend_required_keys(text: str) -> set[str]:
    match = re.search(r"REQUIRED_KEYS\s*=\s*\((.*?)\)\n\n", text, flags=re.S)
    if not match:
        return set()
    block = match.group(1)
    return set(re.findall(r'"([A-Z0-9_]+)"', block))


def _extract_backend_optional_keys(text: str) -> set[str]:
    match = re.search(r"OPTIONAL_KEYS\s*=\s*\((.*?)\)\n\n", text, flags=re.S)
    if not match:
        return set()
    block = match.group(1)
    return set(re.findall(r'"([A-Z0-9_]+)"', block))


def _extract_frontend_required_keys(text: str) -> set[str]:
    match = re.search(r"const required\s*=\s*\[(.*?)\];", text, flags=re.S)
    if not match:
        return set()
    block = match.group(1)
    return set(re.findall(r"'([A-Z0-9_]+)'", block))


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not MANIFEST_PATH.exists():
        return ["missing_env_manifest"]
    if not BACKEND_ENV_CHECK_PATH.exists():
        return ["missing_backend_check_env_script"]
    if not FRONTEND_ENV_CHECK_PATH.exists():
        return ["missing_frontend_check_env_script"]

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    backend_required = set(manifest.get("backend_required") or [])
    backend_optional = set(manifest.get("backend_optional_documented") or [])
    frontend_required = set(manifest.get("frontend_required") or [])
    runtime_switches = set(manifest.get("runtime_switches") or [])
    sensitive_backend_optional = set(manifest.get("sensitive_backend_optional") or [])

    backend_script_text = BACKEND_ENV_CHECK_PATH.read_text(encoding="utf-8")
    frontend_script_text = FRONTEND_ENV_CHECK_PATH.read_text(encoding="utf-8")

    backend_actual = _extract_backend_required_keys(backend_script_text)
    backend_optional_actual = _extract_backend_optional_keys(backend_script_text)
    frontend_actual = _extract_frontend_required_keys(frontend_script_text)

    missing_backend = sorted(backend_required - backend_actual)
    if missing_backend:
        violations.append(f"backend_manifest_missing_in_check_env:{','.join(missing_backend)}")

    missing_backend_optional = sorted(backend_optional - backend_optional_actual)
    if missing_backend_optional:
        violations.append(
            f"backend_optional_manifest_missing_in_check_env:{','.join(missing_backend_optional)}"
        )

    undocumented_backend_optional = sorted(backend_optional_actual - backend_optional)
    if undocumented_backend_optional:
        violations.append(
            f"backend_optional_missing_in_manifest:{','.join(undocumented_backend_optional)}"
        )

    missing_frontend = sorted(frontend_required - frontend_actual)
    if missing_frontend:
        violations.append(f"frontend_manifest_missing_in_check_env:{','.join(missing_frontend)}")

    missing_sensitive_optional = sorted(sensitive_backend_optional - backend_optional)
    if missing_sensitive_optional:
        violations.append(
            f"sensitive_backend_optional_not_documented:{','.join(missing_sensitive_optional)}"
        )

    for switch in runtime_switches:
        if switch not in backend_script_text:
            violations.append(f"runtime_switch_not_documented_in_backend_check_env:{switch}")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[env-secret-manifest-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[env-secret-manifest-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
