from __future__ import annotations

from typing import Any

from app.core.log_redaction import redact_email

BLOCKED_KEY_FRAGMENTS = (
    "email",
    "name",
    "token",
    "password",
    "secret",
    "content",
    "journal",
    "message",
    "phone",
    "address",
)

ALLOWED_PROPS_KEYS = frozenset(
    {
        "loop_version",
        "mood_label",
        "mood_score",
        "question_id",
        "card_id",
        "answered_by",
        "time_spent_sec",
        "content_length",
        "relationship_stage",
        "feature_flags",
        "auto_generated",
        "completion_version",
        "reaction",
        "flow_step",
        "step",
        "event_version",
    }
)

ALLOWED_CONTEXT_KEYS = frozenset(
    {
        "app_version",
        "build",
        "env",
        "locale",
        "tz",
        "route",
        "platform",
        "event_schema_version",
    }
)

ALLOWED_PRIVACY_KEYS = frozenset(
    {
        "pii_redacted",
        "redaction_applied",
        "consent_scope",
        "safety_mode",
    }
)


def sanitize_payload_with_policy(
    *,
    raw_payload: dict[str, Any] | None,
    allowed_keys: frozenset[str],
    max_items: int = 30,
    max_string_length: int = 200,
) -> tuple[dict[str, Any], int, int]:
    sanitized: dict[str, Any] = {}
    blocked_keys = 0
    dropped_items = 0
    if not isinstance(raw_payload, dict):
        return sanitized, blocked_keys, dropped_items

    for key, value in raw_payload.items():
        if len(sanitized) >= max_items:
            dropped_items += 1
            continue
        if not isinstance(key, str):
            dropped_items += 1
            continue
        normalized_key = key.strip().lower()
        if not normalized_key:
            dropped_items += 1
            continue
        if any(fragment in normalized_key for fragment in BLOCKED_KEY_FRAGMENTS):
            blocked_keys += 1
            continue
        if normalized_key not in allowed_keys:
            dropped_items += 1
            continue

        if isinstance(value, bool):
            sanitized[normalized_key] = value
            continue
        if isinstance(value, int):
            sanitized[normalized_key] = value
            continue
        if isinstance(value, float):
            sanitized[normalized_key] = round(value, 6)
            continue
        if isinstance(value, str):
            trimmed = value.strip()
            if not trimmed:
                continue
            if "@" in trimmed:
                trimmed = redact_email(trimmed)
            sanitized[normalized_key] = trimmed[:max_string_length]
            continue
        dropped_items += 1

    return sanitized, blocked_keys, dropped_items
