#!/usr/bin/env python3
"""Validate security-gate.sh contains required step names from manifest."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
SECURITY_GATE_PATH = BACKEND_ROOT / "scripts" / "security-gate.sh"
MANIFEST_PATH = BACKEND_ROOT / "scripts" / "security_gate_steps_manifest.json"

STEP_PATTERN = re.compile(r'run_(?:python|pytest)_step\s+"([^"]+)"')
STEP_LIST_KEYS = (
    "required_fast_steps",
    "required_any_profile_steps",
    "required_shared_contract_steps",
    "required_full_only_steps",
)


def _load_manifest() -> dict:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest_not_object")
    for key in STEP_LIST_KEYS:
        if key not in payload:
            raise ValueError(f"missing_manifest_key:{key}")
        if not isinstance(payload[key], list):
            raise ValueError(f"invalid_manifest_key_type:{key}")
    return payload


def _extract_steps(script_text: str) -> set[str]:
    return {match.group(1).strip() for match in STEP_PATTERN.finditer(script_text) if match.group(1).strip()}


def main() -> int:
    if not SECURITY_GATE_PATH.exists():
        print("[security-gate-steps-manifest] fail: missing_security_gate_script", file=sys.stderr)
        return 1
    if not MANIFEST_PATH.exists():
        print("[security-gate-steps-manifest] fail: missing_manifest", file=sys.stderr)
        return 1

    manifest = _load_manifest()
    script_text = SECURITY_GATE_PATH.read_text(encoding="utf-8")
    available_steps = _extract_steps(script_text)

    missing: list[str] = []
    for key in STEP_LIST_KEYS:
        for step in manifest.get(key, []):
            normalized = str(step).strip()
            if normalized and normalized not in available_steps:
                missing.append(normalized)

    if missing:
        print("[security-gate-steps-manifest] fail", file=sys.stderr)
        for step in missing:
            print(f"- missing_step:{step}", file=sys.stderr)
        return 1

    print("[security-gate-steps-manifest] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
