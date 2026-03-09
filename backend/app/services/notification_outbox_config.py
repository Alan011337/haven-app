"""Configuration/runtime helpers for notification outbox service."""

from __future__ import annotations

from app.core.config import settings
from app.core.settings_domains import get_notification_outbox_settings
from app.services.retry_backoff import compute_exponential_backoff_seconds

EMAIL_FALLBACK_DEFERRED_PREFIX = "email_fallback_deferred"


def settings_bool(*, settings_attr: str, default: bool = False) -> bool:
    raw = getattr(settings, settings_attr, default)
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        normalized = raw.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(default)


def is_notification_outbox_enabled() -> bool:
    return settings_bool(
        settings_attr="NOTIFICATION_OUTBOX_ENABLED",
        default=False,
    )


def retry_base_seconds() -> int:
    return get_notification_outbox_settings().retry_base_seconds


def default_max_attempts() -> int:
    return get_notification_outbox_settings().max_attempts


def default_claim_limit() -> int:
    return get_notification_outbox_settings().claim_limit


def adaptive_batching_enabled() -> bool:
    return get_notification_outbox_settings().adaptive_batching_enabled


def adaptive_max_claim_limit() -> int:
    return get_notification_outbox_settings().adaptive_max_claim_limit


def adaptive_age_scale_threshold_seconds() -> int:
    return get_notification_outbox_settings().adaptive_age_scale_threshold_seconds


def adaptive_age_critical_seconds() -> int:
    return get_notification_outbox_settings().adaptive_age_critical_seconds


def backpressure_depth_threshold() -> int:
    default_threshold = max(50, default_claim_limit() * 10)
    raw = getattr(settings, "NOTIFICATION_OUTBOX_BACKPRESSURE_DEPTH_THRESHOLD", default_threshold)
    return max(1, int(raw))


def backpressure_oldest_age_seconds() -> int:
    raw = getattr(settings, "NOTIFICATION_OUTBOX_BACKPRESSURE_OLDEST_PENDING_SECONDS", 900)
    return max(30, int(raw))


def processing_timeout_seconds() -> int:
    return get_notification_outbox_settings().processing_timeout_seconds


def sent_retention_days() -> int:
    return get_notification_outbox_settings().sent_retention_days


def dead_retention_days() -> int:
    return get_notification_outbox_settings().dead_retention_days


def auto_replay_enabled() -> bool:
    return get_notification_outbox_settings().auto_replay_enabled


def auto_replay_limit() -> int:
    return get_notification_outbox_settings().auto_replay_limit


def auto_replay_min_dead_rows() -> int:
    return get_notification_outbox_settings().auto_replay_min_dead_rows


def auto_replay_min_dead_letter_rate() -> float:
    return get_notification_outbox_settings().auto_replay_min_dead_letter_rate


def dispatch_lock_name() -> str:
    return get_notification_outbox_settings().dispatch_lock_name


def compute_backoff_seconds(*, attempt_count: int) -> int:
    # Exponential backoff with shared policy to keep queue behaviors consistent.
    return max(
        1,
        int(
            compute_exponential_backoff_seconds(
                attempt=max(0, attempt_count - 1),
                base_seconds=float(retry_base_seconds()),
                max_seconds=1800.0,
                jitter_ratio=0.0,
            )
        ),
    )


def encode_email_fallback_deferred_reason(remaining_seconds: int) -> str:
    return f"{EMAIL_FALLBACK_DEFERRED_PREFIX}:{max(1, int(remaining_seconds))}"


def decode_email_fallback_deferred_reason(reason: str | None) -> int | None:
    if not isinstance(reason, str):
        return None
    if not reason.startswith(f"{EMAIL_FALLBACK_DEFERRED_PREFIX}:"):
        return None
    try:
        return max(1, int(reason.split(":", 1)[1]))
    except (TypeError, ValueError, IndexError):
        return None

