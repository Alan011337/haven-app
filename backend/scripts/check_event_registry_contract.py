#!/usr/bin/env python3
"""Event registry contract: required events + cross-file consistency."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "docs" / "data" / "events-registry.json"
FRONTEND_EVENTS_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "relationship-events.ts"
BACKEND_GROWTH_SCHEMA_PATH = REPO_ROOT / "backend" / "app" / "schemas" / "growth.py"

REQUIRED_EVENTS = {
    "daily_sync_submitted",
    "daily_card_revealed",
    "card_answer_submitted",
    "appreciation_sent",
    "daily_loop_completed",
    "ws_connected",
    "ws_disconnected",
    "ws_reconnect_attempted",
    "realtime_fallback_activated",
}

PII_FRAGMENTS = (
    "email@",
    "token",
    "password",
    "cookie",
)


def collect_violations() -> list[str]:
    violations: list[str] = []
    if not REGISTRY_PATH.exists():
        return ["missing_events_registry"]
    if not FRONTEND_EVENTS_PATH.exists():
        return ["missing_frontend_relationship_events"]
    if not BACKEND_GROWTH_SCHEMA_PATH.exists():
        return ["missing_backend_growth_schema"]

    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    events = payload.get("events")
    if not isinstance(events, list):
        return ["events_registry_not_list"]
    event_names = {str(item).strip() for item in events if str(item).strip()}
    missing = sorted(REQUIRED_EVENTS - event_names)
    if missing:
        violations.append(f"missing_required_events:{','.join(missing)}")

    for name in event_names:
        lowered = name.lower()
        for fragment in PII_FRAGMENTS:
            if fragment in lowered:
                violations.append(f"pii_like_fragment_in_event_name:{name}")
                break

    frontend_text = FRONTEND_EVENTS_PATH.read_text(encoding="utf-8")
    for event in (
        "daily_sync_submitted",
        "daily_card_revealed",
        "card_answer_submitted",
        "appreciation_sent",
        "daily_loop_completed",
    ):
        if f"'{event}'" not in frontend_text:
            violations.append(f"frontend_missing_core_event:{event}")

    backend_growth_text = BACKEND_GROWTH_SCHEMA_PATH.read_text(encoding="utf-8")
    for event in (
        "DAILY_SYNC_SUBMITTED = \"daily_sync_submitted\"",
        "DAILY_CARD_REVEALED = \"daily_card_revealed\"",
        "CARD_ANSWER_SUBMITTED = \"card_answer_submitted\"",
        "APPRECIATION_SENT = \"appreciation_sent\"",
        "DAILY_LOOP_COMPLETED = \"daily_loop_completed\"",
    ):
        if event not in backend_growth_text:
            violations.append(f"backend_missing_core_event:{event}")

    return violations


def main() -> int:
    violations = collect_violations()
    if violations:
        print("[event-registry-contract] fail")
        for violation in violations:
            print(f"- {violation}")
        return 1
    print("[event-registry-contract] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
