#!/usr/bin/env python3
"""Policy-as-code gate for PostHog event tracking privacy constraints."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_ROOT.parent

BACKEND_POSTHOG_PATH = BACKEND_ROOT / "app" / "services" / "posthog_events.py"
FRONTEND_POSTHOG_PATH = REPO_ROOT / "frontend" / "src" / "lib" / "posthog.ts"
ALPHA_GATE_DOC_PATH = REPO_ROOT / "docs" / "alpha-gate-v1.md"

REQUIRED_PII_FRAGMENTS: tuple[str, ...] = (
    "email",
    "token",
    "password",
    "secret",
    "authorization",
    "cookie",
    "content",
    "journal",
    "body_text",
    "raw",
)

REQUIRED_DOC_SNIPPETS: tuple[str, ...] = (
    "distinct id",
    "user_id",
    "不使用 email 作 distinct_id",
)


@dataclass(frozen=True)
class EventTrackingPrivacyViolation:
    reason: str
    details: str


def collect_event_tracking_privacy_violations() -> list[EventTrackingPrivacyViolation]:
    violations: list[EventTrackingPrivacyViolation] = []

    if not BACKEND_POSTHOG_PATH.exists():
        return [EventTrackingPrivacyViolation("missing_backend_posthog_file", str(BACKEND_POSTHOG_PATH))]
    if not FRONTEND_POSTHOG_PATH.exists():
        return [EventTrackingPrivacyViolation("missing_frontend_posthog_file", str(FRONTEND_POSTHOG_PATH))]
    if not ALPHA_GATE_DOC_PATH.exists():
        return [EventTrackingPrivacyViolation("missing_alpha_gate_doc", str(ALPHA_GATE_DOC_PATH))]

    backend_text = BACKEND_POSTHOG_PATH.read_text(encoding="utf-8").lower()
    frontend_text = FRONTEND_POSTHOG_PATH.read_text(encoding="utf-8").lower()
    doc_text = ALPHA_GATE_DOC_PATH.read_text(encoding="utf-8").lower()

    for fragment in REQUIRED_PII_FRAGMENTS:
        if fragment not in backend_text:
            violations.append(
                EventTrackingPrivacyViolation(
                    "missing_backend_pii_fragment_guard",
                    f"backend posthog sanitizer missing required fragment: {fragment}",
                )
            )
        if fragment not in frontend_text:
            violations.append(
                EventTrackingPrivacyViolation(
                    "missing_frontend_pii_fragment_guard",
                    f"frontend posthog sanitizer missing required fragment: {fragment}",
                )
            )

    if "def capture_posthog_event" not in backend_text:
        violations.append(
            EventTrackingPrivacyViolation(
                "missing_backend_capture_entry",
                "capture_posthog_event entrypoint must exist.",
            )
        )
    if "distinct_id" not in backend_text:
        violations.append(
            EventTrackingPrivacyViolation(
                "missing_backend_distinct_id",
                "backend capture payload must include distinct_id field.",
            )
        )
    if "identifyposthoguser" not in frontend_text:
        violations.append(
            EventTrackingPrivacyViolation(
                "missing_frontend_identify_entry",
                "frontend identifyPosthogUser helper must exist.",
            )
        )
    if "identifyposthoguser(userid" not in frontend_text.replace(" ", ""):
        violations.append(
            EventTrackingPrivacyViolation(
                "frontend_identify_not_user_id_first",
                "identifyPosthogUser must take userId as first argument.",
            )
        )

    for snippet in REQUIRED_DOC_SNIPPETS:
        if snippet not in doc_text:
            violations.append(
                EventTrackingPrivacyViolation(
                    "missing_privacy_doc_snippet",
                    f"alpha gate doc missing snippet: {snippet}",
                )
            )

    return violations


def main() -> int:
    violations = collect_event_tracking_privacy_violations()
    if not violations:
        print("[event-tracking-privacy-contract] ok: event tracking privacy contract satisfied")
        return 0

    print("[event-tracking-privacy-contract] failed:", file=sys.stderr)
    for violation in violations:
        print(f"  - reason={violation.reason} details={violation.details}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
