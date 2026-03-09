from __future__ import annotations

import json
import logging

from fastapi import HTTPException, status

from app.core.config import settings
from app.services.posthog_events import capture_posthog_event

logger = logging.getLogger(__name__)

_GENERIC_ALPHA_DENY_MESSAGE = "邀請制內測：目前僅開放受邀測試者。"


def _normalized_email_set_from_csv(raw: str) -> set[str]:
    values = set()
    for part in (raw or "").split(","):
        normalized = part.strip().lower()
        if normalized:
            values.add(normalized)
    return values


def _normalized_email_set_from_json(raw: str) -> set[str]:
    cleaned = (raw or "").strip()
    if not cleaned:
        return set()
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("alpha_allowlist_json_parse_failed")
        return set()
    if not isinstance(payload, list):
        logger.warning("alpha_allowlist_json_parse_failed reason=not_list")
        return set()
    values = set()
    for item in payload:
        if not isinstance(item, str):
            continue
        normalized = item.strip().lower()
        if normalized:
            values.add(normalized)
    return values


def alpha_allowlist_enforced() -> bool:
    if not bool(getattr(settings, "ALLOWLIST_ENFORCED", False)):
        return False
    env_name = (getattr(settings, "ENV", "") or "").strip().lower()
    allowed_envs = _normalized_email_set_from_csv(
        str(getattr(settings, "ALLOWLIST_ENFORCED_ENVS", "alpha"))
    )
    if not allowed_envs:
        allowed_envs = {"alpha"}
    return env_name in allowed_envs


def _resolved_allowlist() -> set[str]:
    merged = set()
    merged.update(_normalized_email_set_from_csv(str(getattr(settings, "ALLOWED_TEST_EMAILS", ""))))
    merged.update(_normalized_email_set_from_json(str(getattr(settings, "ALLOWED_TEST_EMAILS_JSON", ""))))
    return merged


def is_email_allowlisted(email: str | None) -> bool:
    if not alpha_allowlist_enforced():
        return True
    normalized = (email or "").strip().lower()
    if not normalized:
        return False
    return normalized in _resolved_allowlist()


def enforce_alpha_allowlist_or_raise(*, email: str | None, auth_stage: str) -> None:
    if is_email_allowlisted(email):
        return
    capture_posthog_event(
        event_name="allowlist_denied",
        distinct_id="system",
        properties={
            "reason": "not_allowlisted",
            "auth_stage": auth_stage,
        },
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=_GENERIC_ALPHA_DENY_MESSAGE,
    )


def alpha_allowlist_deny_message() -> str:
    return _GENERIC_ALPHA_DENY_MESSAGE

