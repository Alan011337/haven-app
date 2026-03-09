from __future__ import annotations

import json
from typing import Any


class SettingsContractError(ValueError):
    pass


def _parse_json_object(raw: str, *, field_name: str) -> dict[str, Any]:
    cleaned = (raw or "").strip()
    if not cleaned:
        return {}
    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise SettingsContractError(f"{field_name} must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise SettingsContractError(f"{field_name} must be a JSON object")
    return payload


def validate_settings_contract(settings: Any) -> list[str]:
    errors: list[str] = []

    if bool(getattr(settings, "POSTHOG_ENABLED", False)):
        if not str(getattr(settings, "POSTHOG_API_KEY", "") or "").strip():
            errors.append("POSTHOG_ENABLED requires POSTHOG_API_KEY")
        if not str(getattr(settings, "POSTHOG_HOST", "") or "").strip():
            errors.append("POSTHOG_ENABLED requires POSTHOG_HOST")

    if str(getattr(settings, "AI_ROUTER_SHARED_STATE_BACKEND", "")).strip().lower() == "redis":
        redis_candidates = (
            str(getattr(settings, "AI_ROUTER_REDIS_URL", "") or "").strip(),
            str(getattr(settings, "REDIS_URL", "") or "").strip(),
            str(getattr(settings, "ABUSE_GUARD_REDIS_URL", "") or "").strip(),
        )
        if not any(redis_candidates):
            errors.append(
                "AI_ROUTER_SHARED_STATE_BACKEND=redis requires AI_ROUTER_REDIS_URL, REDIS_URL, or ABUSE_GUARD_REDIS_URL"
            )

    if str(getattr(settings, "ABUSE_GUARD_STORE_BACKEND", "")).strip().lower() == "redis":
        if not str(getattr(settings, "ABUSE_GUARD_REDIS_URL", "") or "").strip():
            errors.append("ABUSE_GUARD_STORE_BACKEND=redis requires ABUSE_GUARD_REDIS_URL")

    if bool(getattr(settings, "ALLOWLIST_ENFORCED", False)):
        csv_raw = str(getattr(settings, "ALLOWED_TEST_EMAILS", "") or "").strip()
        json_raw = str(getattr(settings, "ALLOWED_TEST_EMAILS_JSON", "") or "").strip()
        if not csv_raw and not json_raw:
            errors.append("ALLOWLIST_ENFORCED requires ALLOWED_TEST_EMAILS or ALLOWED_TEST_EMAILS_JSON")

    for field_name in ("FEATURE_FLAGS_JSON", "FEATURE_KILL_SWITCHES_JSON"):
        try:
            _parse_json_object(str(getattr(settings, field_name, "") or ""), field_name=field_name)
        except SettingsContractError as exc:
            errors.append(str(exc))

    if bool(getattr(settings, "WEBSOCKET_ENABLED", True)):
        if int(getattr(settings, "WS_MAX_CONNECTIONS_PER_USER", 1) or 1) < 1:
            errors.append("WS_MAX_CONNECTIONS_PER_USER must be >= 1 when WEBSOCKET_ENABLED=true")

    return errors
