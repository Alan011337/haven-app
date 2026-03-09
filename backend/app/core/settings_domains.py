from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import settings as global_settings


@dataclass(frozen=True)
class WsSettings:
    max_connections_per_user: int
    max_connections_global: int
    message_rate_limit_count: int
    message_rate_limit_window_seconds: int
    message_backoff_seconds: int
    max_payload_bytes: int
    send_timeout_seconds: float
    send_lock_wait_seconds: float
    max_pending_sends_per_user: int
    scope_include_ip: bool
    scope_include_device: bool
    scope_include_partner_pair: bool
    connection_rate_limit_count: int
    connection_rate_limit_window_seconds: int


@dataclass(frozen=True)
class PushDispatchSettings:
    max_active_subscriptions: int
    batch_size: int
    max_concurrency: int
    retry_attempts: int
    retry_base_seconds: float


@dataclass(frozen=True)
class BillingWebhookSettings:
    retry_max_attempts: int
    retry_base_seconds: int
    signature_tolerance_seconds: int
    async_mode: bool


@dataclass(frozen=True)
class TimelineCursorSettings:
    max_limit: int
    query_budget: int
    signing_key: str | None
    require_signature: bool
    allow_default_signing_key: bool


@dataclass(frozen=True)
class NotificationOutboxSettings:
    max_attempts: int
    retry_base_seconds: int
    claim_limit: int
    adaptive_batching_enabled: bool
    adaptive_max_claim_limit: int
    adaptive_age_scale_threshold_seconds: int
    adaptive_age_critical_seconds: int
    processing_timeout_seconds: int
    sent_retention_days: int
    dead_retention_days: int
    auto_replay_enabled: bool
    auto_replay_limit: int
    auto_replay_min_dead_rows: int
    auto_replay_min_dead_letter_rate: float
    dispatch_lock_name: str
    backlog_throttle_enabled: bool
    backlog_throttle_depth_threshold: int
    backlog_throttle_oldest_pending_seconds_threshold: int
    backlog_throttle_exempt_event_types: tuple[str, ...]
    backlog_throttle_exempt_action_types: tuple[str, ...]


@dataclass(frozen=True)
class DynamicContentSettings:
    ai_timeout_seconds: float
    ai_max_retries: int
    ai_backoff_base_seconds: float
    ai_failure_cooldown_seconds: float
    provider_init_retry_seconds: float
    shadow_mode: bool
    cooldown_store_retry_seconds: float
    degraded_fallback_ratio_threshold: float
    degraded_min_attempts: int
    degraded_duration_seconds: float
    degraded_recovery_fallback_ratio_threshold: float
    degraded_recovery_min_attempts: int
    degraded_extension_seconds: float


def _as_int(source: Any, name: str, default: int) -> int:
    try:
        return int(getattr(source, name, default))
    except (TypeError, ValueError):
        return int(default)


def _as_float(source: Any, name: str, default: float) -> float:
    try:
        return float(getattr(source, name, default))
    except (TypeError, ValueError):
        return float(default)


def _as_bool(source: Any, name: str, default: bool) -> bool:
    value = getattr(source, name, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(default)


def _as_csv_tuple(source: Any, name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    raw = getattr(source, name, None)
    if raw is None:
        return default
    if isinstance(raw, str):
        items = [item.strip().lower() for item in raw.split(",")]
        normalized = tuple(item for item in items if item)
        return normalized or default
    if isinstance(raw, (list, tuple, set)):
        normalized = tuple(
            str(item).strip().lower()
            for item in raw
            if str(item).strip()
        )
        return normalized or default
    return default


def load_ws_settings(source: Any) -> WsSettings:
    return WsSettings(
        max_connections_per_user=max(1, _as_int(source, "WS_MAX_CONNECTIONS_PER_USER", 1)),
        max_connections_global=max(1, _as_int(source, "WS_MAX_CONNECTIONS_GLOBAL", 2000)),
        message_rate_limit_count=max(1, _as_int(source, "WS_MESSAGE_RATE_LIMIT_COUNT", 120)),
        message_rate_limit_window_seconds=max(
            1,
            _as_int(source, "WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS", 60),
        ),
        message_backoff_seconds=max(1, _as_int(source, "WS_MESSAGE_BACKOFF_SECONDS", 30)),
        max_payload_bytes=max(64, _as_int(source, "WS_MAX_PAYLOAD_BYTES", 4096)),
        send_timeout_seconds=max(0.05, _as_float(source, "WS_SEND_TIMEOUT_SECONDS", 2.0)),
        send_lock_wait_seconds=max(0.01, _as_float(source, "WS_SEND_LOCK_WAIT_SECONDS", 0.1)),
        max_pending_sends_per_user=max(1, _as_int(source, "WS_MAX_PENDING_SENDS_PER_USER", 8)),
        scope_include_ip=_as_bool(source, "WS_MESSAGE_SCOPE_INCLUDE_IP", True),
        scope_include_device=_as_bool(source, "WS_MESSAGE_SCOPE_INCLUDE_DEVICE", True),
        scope_include_partner_pair=_as_bool(source, "WS_MESSAGE_SCOPE_INCLUDE_PARTNER_PAIR", True),
        connection_rate_limit_count=max(
            1,
            _as_int(source, "WS_CONNECTION_RATE_LIMIT_COUNT", 60),
        ),
        connection_rate_limit_window_seconds=max(
            1,
            _as_int(source, "WS_CONNECTION_RATE_LIMIT_WINDOW_SECONDS", 60),
        ),
    )


def load_push_dispatch_settings(source: Any) -> PushDispatchSettings:
    max_active = max(1, _as_int(source, "PUSH_DISPATCH_MAX_ACTIVE_SUBSCRIPTIONS", 50))
    batch_size = max(1, _as_int(source, "PUSH_DISPATCH_BATCH_SIZE", 20))
    return PushDispatchSettings(
        max_active_subscriptions=max_active,
        batch_size=min(max_active, batch_size),
        max_concurrency=max(1, _as_int(source, "PUSH_DISPATCH_MAX_CONCURRENCY", 5)),
        retry_attempts=max(0, _as_int(source, "PUSH_DISPATCH_RETRY_ATTEMPTS", 1)),
        retry_base_seconds=max(0.05, _as_float(source, "PUSH_DISPATCH_RETRY_BASE_SECONDS", 0.25)),
    )


def load_billing_webhook_settings(source: Any) -> BillingWebhookSettings:
    return BillingWebhookSettings(
        retry_max_attempts=max(1, _as_int(source, "BILLING_WEBHOOK_RETRY_MAX_ATTEMPTS", 3)),
        retry_base_seconds=max(1, _as_int(source, "BILLING_WEBHOOK_RETRY_BASE_SECONDS", 30)),
        signature_tolerance_seconds=max(
            1,
            _as_int(source, "BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS", 300),
        ),
        async_mode=_as_bool(source, "BILLING_STRIPE_WEBHOOK_ASYNC_MODE", False),
    )


def load_timeline_cursor_settings(source: Any) -> TimelineCursorSettings:
    signing_key = getattr(source, "TIMELINE_CURSOR_SIGNING_KEY", None)
    normalized_signing_key = (
        str(signing_key).strip() if isinstance(signing_key, str) and signing_key.strip() else None
    )
    return TimelineCursorSettings(
        max_limit=max(1, _as_int(source, "TIMELINE_CURSOR_MAX_LIMIT", 100)),
        query_budget=max(4, _as_int(source, "TIMELINE_CURSOR_QUERY_BUDGET", 500)),
        signing_key=normalized_signing_key,
        require_signature=_as_bool(source, "TIMELINE_CURSOR_REQUIRE_SIGNATURE", True),
        allow_default_signing_key=_as_bool(
            source,
            "TIMELINE_CURSOR_ALLOW_DEFAULT_SIGNING_KEY",
            False,
        ),
    )


def load_notification_outbox_settings(source: Any) -> NotificationOutboxSettings:
    raw_dispatch_lock_name = str(
        getattr(source, "NOTIFICATION_OUTBOX_DISPATCH_LOCK_NAME", "notification-outbox-dispatch")
    ).strip()
    return NotificationOutboxSettings(
        max_attempts=max(1, _as_int(source, "NOTIFICATION_OUTBOX_MAX_ATTEMPTS", 3)),
        retry_base_seconds=max(1, _as_int(source, "NOTIFICATION_OUTBOX_RETRY_BASE_SECONDS", 30)),
        claim_limit=max(1, _as_int(source, "NOTIFICATION_OUTBOX_CLAIM_LIMIT", 50)),
        adaptive_batching_enabled=_as_bool(
            source,
            "NOTIFICATION_OUTBOX_ADAPTIVE_BATCHING_ENABLED",
            True,
        ),
        adaptive_max_claim_limit=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_ADAPTIVE_MAX_CLAIM_LIMIT", 500),
        ),
        adaptive_age_scale_threshold_seconds=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_ADAPTIVE_AGE_SCALE_THRESHOLD_SECONDS", 300),
        ),
        adaptive_age_critical_seconds=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_ADAPTIVE_AGE_CRITICAL_SECONDS", 1200),
        ),
        processing_timeout_seconds=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_PROCESSING_TIMEOUT_SECONDS", 300),
        ),
        sent_retention_days=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_SENT_RETENTION_DAYS", 14),
        ),
        dead_retention_days=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_DEAD_RETENTION_DAYS", 30),
        ),
        auto_replay_enabled=_as_bool(
            source,
            "NOTIFICATION_OUTBOX_AUTO_REPLAY_ENABLED",
            True,
        ),
        auto_replay_limit=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_AUTO_REPLAY_LIMIT", 100),
        ),
        auto_replay_min_dead_rows=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_AUTO_REPLAY_MIN_DEAD_ROWS", 50),
        ),
        auto_replay_min_dead_letter_rate=min(
            1.0,
            max(
                0.0,
                _as_float(source, "NOTIFICATION_OUTBOX_AUTO_REPLAY_MIN_DEAD_LETTER_RATE", 0.2),
            ),
        ),
        dispatch_lock_name=raw_dispatch_lock_name or "notification-outbox-dispatch",
        backlog_throttle_enabled=_as_bool(
            source,
            "NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_ENABLED",
            True,
        ),
        backlog_throttle_depth_threshold=max(
            1,
            _as_int(source, "NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_DEPTH_THRESHOLD", 2000),
        ),
        backlog_throttle_oldest_pending_seconds_threshold=max(
            1,
            _as_int(
                source,
                "NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_OLDEST_PENDING_SECONDS_THRESHOLD",
                1200,
            ),
        ),
        backlog_throttle_exempt_event_types=_as_csv_tuple(
            source,
            "NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_EXEMPT_EVENT_TYPES",
            (),
        ),
        backlog_throttle_exempt_action_types=_as_csv_tuple(
            source,
            "NOTIFICATION_OUTBOX_BACKLOG_THROTTLE_EXEMPT_ACTION_TYPES",
            ("journal",),
        ),
    )


def load_dynamic_content_settings(source: Any) -> DynamicContentSettings:
    return DynamicContentSettings(
        ai_timeout_seconds=max(0.1, _as_float(source, "DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS", 12.0)),
        ai_max_retries=max(0, _as_int(source, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 2)),
        ai_backoff_base_seconds=max(
            0.01,
            _as_float(source, "DYNAMIC_CONTENT_AI_BACKOFF_BASE_SECONDS", 0.75),
        ),
        ai_failure_cooldown_seconds=max(
            0.0,
            _as_float(source, "DYNAMIC_CONTENT_AI_FAILURE_COOLDOWN_SECONDS", 300.0),
        ),
        provider_init_retry_seconds=max(
            1.0,
            _as_float(source, "DYNAMIC_CONTENT_PROVIDER_INIT_RETRY_SECONDS", 60.0),
        ),
        shadow_mode=_as_bool(source, "DYNAMIC_CONTENT_SHADOW_MODE", False),
        cooldown_store_retry_seconds=max(
            1.0,
            _as_float(source, "DYNAMIC_CONTENT_COOLDOWN_STORE_RETRY_SECONDS", 60.0),
        ),
        degraded_fallback_ratio_threshold=min(
            1.0,
            max(
                0.0,
                _as_float(source, "DYNAMIC_CONTENT_DEGRADED_FALLBACK_RATIO_THRESHOLD", 0.6),
            ),
        ),
        degraded_min_attempts=max(1, _as_int(source, "DYNAMIC_CONTENT_DEGRADED_MIN_ATTEMPTS", 10)),
        degraded_duration_seconds=max(
            1.0,
            _as_float(source, "DYNAMIC_CONTENT_DEGRADED_DURATION_SECONDS", 900.0),
        ),
        degraded_recovery_fallback_ratio_threshold=min(
            1.0,
            max(
                0.0,
                _as_float(
                    source,
                    "DYNAMIC_CONTENT_DEGRADED_RECOVERY_FALLBACK_RATIO_THRESHOLD",
                    0.35,
                ),
            ),
        ),
        degraded_recovery_min_attempts=max(
            1,
            _as_int(source, "DYNAMIC_CONTENT_DEGRADED_RECOVERY_MIN_ATTEMPTS", 10),
        ),
        degraded_extension_seconds=max(
            1.0,
            _as_float(source, "DYNAMIC_CONTENT_DEGRADED_EXTENSION_SECONDS", 300.0),
        ),
    )


@lru_cache(maxsize=16)
def _cached_ws_settings(
    max_connections_per_user: int,
    max_connections_global: int,
    message_rate_limit_count: int,
    message_rate_limit_window_seconds: int,
    message_backoff_seconds: int,
    max_payload_bytes: int,
    send_timeout_seconds: float,
    send_lock_wait_seconds: float,
    max_pending_sends_per_user: int,
    scope_include_ip: bool,
    scope_include_device: bool,
    scope_include_partner_pair: bool,
    connection_rate_limit_count: int,
    connection_rate_limit_window_seconds: int,
) -> WsSettings:
    return WsSettings(
        max_connections_per_user=max_connections_per_user,
        max_connections_global=max_connections_global,
        message_rate_limit_count=message_rate_limit_count,
        message_rate_limit_window_seconds=message_rate_limit_window_seconds,
        message_backoff_seconds=message_backoff_seconds,
        max_payload_bytes=max_payload_bytes,
        send_timeout_seconds=send_timeout_seconds,
        send_lock_wait_seconds=send_lock_wait_seconds,
        max_pending_sends_per_user=max_pending_sends_per_user,
        scope_include_ip=scope_include_ip,
        scope_include_device=scope_include_device,
        scope_include_partner_pair=scope_include_partner_pair,
        connection_rate_limit_count=connection_rate_limit_count,
        connection_rate_limit_window_seconds=connection_rate_limit_window_seconds,
    )


def get_ws_settings() -> WsSettings:
    parsed = load_ws_settings(global_settings)
    return _cached_ws_settings(
        parsed.max_connections_per_user,
        parsed.max_connections_global,
        parsed.message_rate_limit_count,
        parsed.message_rate_limit_window_seconds,
        parsed.message_backoff_seconds,
        parsed.max_payload_bytes,
        parsed.send_timeout_seconds,
        parsed.send_lock_wait_seconds,
        parsed.max_pending_sends_per_user,
        parsed.scope_include_ip,
        parsed.scope_include_device,
        parsed.scope_include_partner_pair,
        parsed.connection_rate_limit_count,
        parsed.connection_rate_limit_window_seconds,
    )


@lru_cache(maxsize=16)
def _cached_push_dispatch_settings(
    max_active_subscriptions: int,
    batch_size: int,
    max_concurrency: int,
    retry_attempts: int,
    retry_base_seconds: float,
) -> PushDispatchSettings:
    return PushDispatchSettings(
        max_active_subscriptions=max_active_subscriptions,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        retry_attempts=retry_attempts,
        retry_base_seconds=retry_base_seconds,
    )


def get_push_dispatch_settings() -> PushDispatchSettings:
    parsed = load_push_dispatch_settings(global_settings)
    return _cached_push_dispatch_settings(
        parsed.max_active_subscriptions,
        parsed.batch_size,
        parsed.max_concurrency,
        parsed.retry_attempts,
        parsed.retry_base_seconds,
    )


@lru_cache(maxsize=16)
def _cached_billing_webhook_settings(
    retry_max_attempts: int,
    retry_base_seconds: int,
    signature_tolerance_seconds: int,
    async_mode: bool,
) -> BillingWebhookSettings:
    return BillingWebhookSettings(
        retry_max_attempts=retry_max_attempts,
        retry_base_seconds=retry_base_seconds,
        signature_tolerance_seconds=signature_tolerance_seconds,
        async_mode=async_mode,
    )


def get_billing_webhook_settings() -> BillingWebhookSettings:
    parsed = load_billing_webhook_settings(global_settings)
    return _cached_billing_webhook_settings(
        parsed.retry_max_attempts,
        parsed.retry_base_seconds,
        parsed.signature_tolerance_seconds,
        parsed.async_mode,
    )


@lru_cache(maxsize=16)
def _cached_timeline_cursor_settings(
    max_limit: int,
    query_budget: int,
    signing_key: str | None,
    require_signature: bool,
    allow_default_signing_key: bool,
) -> TimelineCursorSettings:
    return TimelineCursorSettings(
        max_limit=max_limit,
        query_budget=query_budget,
        signing_key=signing_key,
        require_signature=require_signature,
        allow_default_signing_key=allow_default_signing_key,
    )


def get_timeline_cursor_settings() -> TimelineCursorSettings:
    parsed = load_timeline_cursor_settings(global_settings)
    return _cached_timeline_cursor_settings(
        parsed.max_limit,
        parsed.query_budget,
        parsed.signing_key,
        parsed.require_signature,
        parsed.allow_default_signing_key,
    )


@lru_cache(maxsize=16)
def _cached_notification_outbox_settings(
    max_attempts: int,
    retry_base_seconds: int,
    claim_limit: int,
    adaptive_batching_enabled: bool,
    adaptive_max_claim_limit: int,
    adaptive_age_scale_threshold_seconds: int,
    adaptive_age_critical_seconds: int,
    processing_timeout_seconds: int,
    sent_retention_days: int,
    dead_retention_days: int,
    auto_replay_enabled: bool,
    auto_replay_limit: int,
    auto_replay_min_dead_rows: int,
    auto_replay_min_dead_letter_rate: float,
    dispatch_lock_name: str,
    backlog_throttle_enabled: bool,
    backlog_throttle_depth_threshold: int,
    backlog_throttle_oldest_pending_seconds_threshold: int,
    backlog_throttle_exempt_event_types: tuple[str, ...],
    backlog_throttle_exempt_action_types: tuple[str, ...],
) -> NotificationOutboxSettings:
    return NotificationOutboxSettings(
        max_attempts=max_attempts,
        retry_base_seconds=retry_base_seconds,
        claim_limit=claim_limit,
        adaptive_batching_enabled=adaptive_batching_enabled,
        adaptive_max_claim_limit=adaptive_max_claim_limit,
        adaptive_age_scale_threshold_seconds=adaptive_age_scale_threshold_seconds,
        adaptive_age_critical_seconds=adaptive_age_critical_seconds,
        processing_timeout_seconds=processing_timeout_seconds,
        sent_retention_days=sent_retention_days,
        dead_retention_days=dead_retention_days,
        auto_replay_enabled=auto_replay_enabled,
        auto_replay_limit=auto_replay_limit,
        auto_replay_min_dead_rows=auto_replay_min_dead_rows,
        auto_replay_min_dead_letter_rate=auto_replay_min_dead_letter_rate,
        dispatch_lock_name=dispatch_lock_name,
        backlog_throttle_enabled=backlog_throttle_enabled,
        backlog_throttle_depth_threshold=backlog_throttle_depth_threshold,
        backlog_throttle_oldest_pending_seconds_threshold=backlog_throttle_oldest_pending_seconds_threshold,
        backlog_throttle_exempt_event_types=backlog_throttle_exempt_event_types,
        backlog_throttle_exempt_action_types=backlog_throttle_exempt_action_types,
    )


def get_notification_outbox_settings() -> NotificationOutboxSettings:
    parsed = load_notification_outbox_settings(global_settings)
    return _cached_notification_outbox_settings(
        parsed.max_attempts,
        parsed.retry_base_seconds,
        parsed.claim_limit,
        parsed.adaptive_batching_enabled,
        parsed.adaptive_max_claim_limit,
        parsed.adaptive_age_scale_threshold_seconds,
        parsed.adaptive_age_critical_seconds,
        parsed.processing_timeout_seconds,
        parsed.sent_retention_days,
        parsed.dead_retention_days,
        parsed.auto_replay_enabled,
        parsed.auto_replay_limit,
        parsed.auto_replay_min_dead_rows,
        parsed.auto_replay_min_dead_letter_rate,
        parsed.dispatch_lock_name,
        parsed.backlog_throttle_enabled,
        parsed.backlog_throttle_depth_threshold,
        parsed.backlog_throttle_oldest_pending_seconds_threshold,
        parsed.backlog_throttle_exempt_event_types,
        parsed.backlog_throttle_exempt_action_types,
    )


@lru_cache(maxsize=16)
def _cached_dynamic_content_settings(
    ai_timeout_seconds: float,
    ai_max_retries: int,
    ai_backoff_base_seconds: float,
    ai_failure_cooldown_seconds: float,
    provider_init_retry_seconds: float,
    shadow_mode: bool,
    cooldown_store_retry_seconds: float,
    degraded_fallback_ratio_threshold: float,
    degraded_min_attempts: int,
    degraded_duration_seconds: float,
    degraded_recovery_fallback_ratio_threshold: float,
    degraded_recovery_min_attempts: int,
    degraded_extension_seconds: float,
) -> DynamicContentSettings:
    return DynamicContentSettings(
        ai_timeout_seconds=ai_timeout_seconds,
        ai_max_retries=ai_max_retries,
        ai_backoff_base_seconds=ai_backoff_base_seconds,
        ai_failure_cooldown_seconds=ai_failure_cooldown_seconds,
        provider_init_retry_seconds=provider_init_retry_seconds,
        shadow_mode=shadow_mode,
        cooldown_store_retry_seconds=cooldown_store_retry_seconds,
        degraded_fallback_ratio_threshold=degraded_fallback_ratio_threshold,
        degraded_min_attempts=degraded_min_attempts,
        degraded_duration_seconds=degraded_duration_seconds,
        degraded_recovery_fallback_ratio_threshold=degraded_recovery_fallback_ratio_threshold,
        degraded_recovery_min_attempts=degraded_recovery_min_attempts,
        degraded_extension_seconds=degraded_extension_seconds,
    )


def get_dynamic_content_settings() -> DynamicContentSettings:
    parsed = load_dynamic_content_settings(global_settings)
    return _cached_dynamic_content_settings(
        parsed.ai_timeout_seconds,
        parsed.ai_max_retries,
        parsed.ai_backoff_base_seconds,
        parsed.ai_failure_cooldown_seconds,
        parsed.provider_init_retry_seconds,
        parsed.shadow_mode,
        parsed.cooldown_store_retry_seconds,
        parsed.degraded_fallback_ratio_threshold,
        parsed.degraded_min_attempts,
        parsed.degraded_duration_seconds,
        parsed.degraded_recovery_fallback_ratio_threshold,
        parsed.degraded_recovery_min_attempts,
        parsed.degraded_extension_seconds,
    )


def clear_settings_domain_cache() -> None:
    _cached_ws_settings.cache_clear()
    _cached_push_dispatch_settings.cache_clear()
    _cached_billing_webhook_settings.cache_clear()
    _cached_timeline_cursor_settings.cache_clear()
    _cached_notification_outbox_settings.cache_clear()
    _cached_dynamic_content_settings.cache_clear()
