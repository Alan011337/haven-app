from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class RuntimeFeatureSwitches:
    websocket_enabled: bool
    webpush_enabled: bool
    push_notifications_enabled: bool
    email_notifications_enabled: bool
    timeline_cursor_enabled: bool
    safety_mode_enabled: bool


def get_runtime_feature_switches() -> RuntimeFeatureSwitches:
    return RuntimeFeatureSwitches(
        websocket_enabled=bool(getattr(settings, "WEBSOCKET_ENABLED", True)),
        webpush_enabled=bool(getattr(settings, "WEBPUSH_ENABLED", True)),
        push_notifications_enabled=bool(getattr(settings, "PUSH_NOTIFICATIONS_ENABLED", False)),
        email_notifications_enabled=bool(getattr(settings, "EMAIL_NOTIFICATIONS_ENABLED", True)),
        timeline_cursor_enabled=bool(getattr(settings, "TIMELINE_CURSOR_ENABLED", False)),
        safety_mode_enabled=bool(getattr(settings, "SAFETY_MODE_ENABLED", True)),
    )
