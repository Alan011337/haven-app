# backend/app/services/notification_trigger_matrix.py
"""
Reads docs/security/notification-trigger-matrix.json and resolves channel fallback
order for event types. Respects kill_switch (global_disable, per_channel_disable).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Path relative to repo root (Haven/)
_MATRIX_PATH = Path(__file__).resolve().parents[3] / "docs" / "security" / "notification-trigger-matrix.json"

# Event type alias: "journal" -> "journal_created" for matrix lookup
_EVENT_TYPE_ALIAS: dict[str, str] = {
    "journal": "journal_created",
}


def _load_matrix() -> dict[str, Any]:
    """Load and parse the notification trigger matrix JSON."""
    if not _MATRIX_PATH.exists():
        logger.warning("Notification trigger matrix not found: %s", _MATRIX_PATH)
        return _empty_matrix()
    try:
        with open(_MATRIX_PATH, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else _empty_matrix()
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to load notification trigger matrix: %s", type(exc).__name__)
        return _empty_matrix()


def _empty_matrix() -> dict[str, Any]:
    return {
        "triggers": {},
        "channels": ["push", "email", "in_app_ws"],
        "kill_switch": {"global_disable": False, "per_channel_disable": {}},
    }


_matrix_cache: dict[str, Any] | None = None


def _get_matrix() -> dict[str, Any]:
    global _matrix_cache
    if _matrix_cache is None:
        _matrix_cache = _load_matrix()
    return _matrix_cache


def reset_matrix_cache_for_test() -> None:
    """Reset cached matrix for tests."""
    global _matrix_cache
    _matrix_cache = None


def resolve_event_type(event_type: str) -> str:
    """Resolve event type to matrix key (e.g. journal -> journal_created)."""
    return _EVENT_TYPE_ALIAS.get(event_type, event_type)


def get_channels_for_event(event_type: str) -> list[str]:
    """
    Resolve channel fallback order for an event type.
    Returns channels in fallback_priority order, filtered by:
    - trigger enabled
    - kill_switch global_disable
    - kill_switch per_channel_disable
    """
    matrix = _get_matrix()
    kill = matrix.get("kill_switch") or {}
    if kill.get("global_disable"):
        return []

    resolved = resolve_event_type(event_type)
    triggers = matrix.get("triggers") or {}
    trigger = triggers.get(resolved)
    if not trigger or not trigger.get("enabled", True):
        return []

    fallback = trigger.get("fallback_priority") or trigger.get("channels") or []
    if not isinstance(fallback, list):
        return []

    per_channel = kill.get("per_channel_disable") or {}
    result: list[str] = []
    for ch in fallback:
        if isinstance(ch, str) and not per_channel.get(ch, False):
            result.append(ch)
    return result


def get_throttle_window_seconds(event_type: str) -> int:
    """Return throttle window in seconds for the event type, or 0 if not configured."""
    matrix = _get_matrix()
    triggers = matrix.get("triggers") or {}
    resolved = resolve_event_type(event_type)
    trigger = triggers.get(resolved)
    if not trigger:
        return 0
    val = trigger.get("throttle_window_seconds", 0)
    return max(0, int(val)) if isinstance(val, (int, float)) else 0


def is_channel_disabled(channel: str) -> bool:
    """Check if a channel is disabled by kill_switch."""
    matrix = _get_matrix()
    kill = matrix.get("kill_switch") or {}
    if kill.get("global_disable"):
        return True
    per_channel = kill.get("per_channel_disable") or {}
    return bool(per_channel.get(channel, False))
