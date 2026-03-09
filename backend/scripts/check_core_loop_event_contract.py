#!/usr/bin/env python3
"""Fail-closed contract check for core-loop frontend/backend event alignment."""

from __future__ import annotations

from pathlib import Path
import re
import sys

from app.schemas.growth import CoreLoopEventName
from app.services.events_sanitize import ALLOWED_PROPS_KEYS

REPO_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_CONTRACT_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "core-loop-event-contract.ts"
FRONTEND_TRACKER_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "relationship-events.ts"


def _extract_string_array(text: str, const_name: str) -> list[str]:
    match = re.search(
        rf"{const_name}\s*=\s*\[(?P<body>.*?)\]\s*as const",
        text,
        flags=re.DOTALL,
    )
    if not match:
        return []
    body = match.group("body")
    return [value for _, value in re.findall(r"(['\"])(.*?)\1", body)]


def main() -> int:
    violations: list[str] = []

    if not FRONTEND_CONTRACT_PATH.exists():
        print(
            f"[core-loop-event-contract] fail: missing {FRONTEND_CONTRACT_PATH.relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
        return 1
    if not FRONTEND_TRACKER_PATH.exists():
        print(
            f"[core-loop-event-contract] fail: missing {FRONTEND_TRACKER_PATH.relative_to(REPO_ROOT)}",
            file=sys.stderr,
        )
        return 1

    contract_text = FRONTEND_CONTRACT_PATH.read_text(encoding="utf-8")
    tracker_text = FRONTEND_TRACKER_PATH.read_text(encoding="utf-8")

    frontend_event_names = set(_extract_string_array(contract_text, "CORE_LOOP_EVENT_NAMES"))
    backend_event_names = {item.value for item in CoreLoopEventName}
    if frontend_event_names != backend_event_names:
        missing_frontend = sorted(backend_event_names - frontend_event_names)
        missing_backend = sorted(frontend_event_names - backend_event_names)
        violations.append(
            "event_name_mismatch:"
            f"missing_frontend={missing_frontend}:missing_backend={missing_backend}"
        )

    frontend_props = set(_extract_string_array(contract_text, "CORE_LOOP_ALLOWED_PROPS"))
    backend_props = {key.lower() for key in ALLOWED_PROPS_KEYS}
    if frontend_props != backend_props:
        missing_frontend_props = sorted(backend_props - frontend_props)
        missing_backend_props = sorted(frontend_props - backend_props)
        violations.append(
            "props_key_mismatch:"
            f"missing_frontend={missing_frontend_props}:missing_backend={missing_backend_props}"
        )

    required_tracker_markers = (
        "sanitizeCoreLoopProps",
        "/users/events/core-loop",
    )
    for marker in required_tracker_markers:
        if marker not in tracker_text:
            violations.append(f"tracker_missing_marker:{marker}")

    if violations:
        print("[core-loop-event-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1

    print("[core-loop-event-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

