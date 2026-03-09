from __future__ import annotations

from collections import deque
import hashlib
import json
import logging
from threading import Lock
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_
from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.events_log import EventsLog
from app.services.events_runtime_metrics import events_runtime_metrics
from app.services.events_sanitize import (
    ALLOWED_CONTEXT_KEYS as _ALLOWED_CONTEXT_KEYS,
    ALLOWED_PRIVACY_KEYS as _ALLOWED_PRIVACY_KEYS,
    ALLOWED_PROPS_KEYS as _ALLOWED_PROPS_KEYS,
    sanitize_payload_with_policy as _sanitize_payload_with_policy,
)

logger = logging.getLogger(__name__)

_DAILY_LOOP_REQUIRED_EVENTS = frozenset(
    {
        "daily_sync_submitted",
        "daily_card_revealed",
        "card_answer_submitted",
        "appreciation_sent",
    }
)
_DAILY_LOOP_COMPLETED_EVENT = "daily_loop_completed"

_INGEST_GUARD_LOCK = Lock()
_INGEST_GUARD_HITS: dict[str, deque[datetime]] = {}
_INGEST_GUARD_STATE_LOCK = Lock()
_INGEST_GUARD_STATE: dict[str, Any] = {
    "configured_backend": "memory",
    "active_backend": "memory",
    "redis_degraded_mode": False,
}
_INGEST_GUARD_REDIS_STORE: Any | None = None
_INGEST_GUARD_REDIS_INIT_FAILED: bool = False


@dataclass(frozen=True)
class CoreLoopRecordResult:
    accepted: bool
    deduped: bool


def _json_max_bytes() -> int:
    try:
        return max(256, int(getattr(settings, "EVENTS_LOG_JSON_MAX_BYTES", 1800)))
    except (TypeError, ValueError):
        return 1800


def _json_total_max_bytes() -> int:
    try:
        return max(512, int(getattr(settings, "EVENTS_LOG_TOTAL_JSON_MAX_BYTES", 2400)))
    except (TypeError, ValueError):
        return 2400


def _serialize_json_payload(payload: dict[str, Any]) -> tuple[str | None, bool]:
    if not payload:
        return None, False
    encoded = json.dumps(payload, ensure_ascii=True, sort_keys=True)
    if len(encoded.encode("utf-8")) > _json_max_bytes():
        return None, True
    return encoded, False


def _build_dedupe_key(
    *,
    user_id: uuid.UUID,
    event_name: str,
    event_id: str,
) -> str:
    payload = f"{user_id}:{event_name}:{event_id}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _configured_ingest_backend() -> str:
    env_name = str(getattr(settings, "ENV", "development") or "development").strip().lower()
    default_backend = "redis" if env_name in {"alpha", "prod", "production"} else "memory"
    raw = str(getattr(settings, "EVENTS_LOG_INGEST_STORE_BACKEND", default_backend) or default_backend)
    backend = raw.strip().lower()
    return backend if backend in {"memory", "redis"} else "memory"


def _configured_ingest_redis_url() -> str:
    direct = str(getattr(settings, "EVENTS_LOG_INGEST_REDIS_URL", "") or "").strip()
    if direct:
        return direct
    return str(getattr(settings, "ABUSE_GUARD_REDIS_URL", "") or "").strip()


def _configured_ingest_redis_key_prefix() -> str:
    raw = str(getattr(settings, "EVENTS_LOG_INGEST_REDIS_KEY_PREFIX", "haven:events-ingest:") or "").strip()
    if raw:
        return raw
    return "haven:events-ingest:"


def _set_ingest_guard_state(*, configured_backend: str, active_backend: str, redis_degraded_mode: bool) -> None:
    with _INGEST_GUARD_STATE_LOCK:
        _INGEST_GUARD_STATE["configured_backend"] = configured_backend
        _INGEST_GUARD_STATE["active_backend"] = active_backend
        _INGEST_GUARD_STATE["redis_degraded_mode"] = bool(redis_degraded_mode)


def get_core_loop_ingest_guard_state() -> dict[str, Any]:
    with _INGEST_GUARD_STATE_LOCK:
        return dict(_INGEST_GUARD_STATE)


def _get_redis_ingest_guard_store() -> Any:
    global _INGEST_GUARD_REDIS_STORE
    global _INGEST_GUARD_REDIS_INIT_FAILED
    with _INGEST_GUARD_STATE_LOCK:
        if _INGEST_GUARD_REDIS_STORE is not None:
            return _INGEST_GUARD_REDIS_STORE
        if _INGEST_GUARD_REDIS_INIT_FAILED:
            raise RuntimeError("redis_ingest_guard_unavailable")
        redis_url = _configured_ingest_redis_url()
        if not redis_url:
            _INGEST_GUARD_REDIS_INIT_FAILED = True
            raise RuntimeError("events_ingest_redis_url_missing")
        try:
            from app.services.abuse_state_store import RedisAbuseStateStore

            _INGEST_GUARD_REDIS_STORE = RedisAbuseStateStore(
                redis_url=redis_url,
                key_prefix=_configured_ingest_redis_key_prefix(),
            )
            return _INGEST_GUARD_REDIS_STORE
        except Exception as exc:  # pragma: no cover - exercised via tests by patching constructor.
            _INGEST_GUARD_REDIS_INIT_FAILED = True
            raise RuntimeError("events_ingest_redis_init_failed") from exc


def allow_core_loop_event_ingest(
    *,
    user_id: uuid.UUID,
    event_name: str,
) -> tuple[bool, int]:
    limit_count = max(1, int(getattr(settings, "EVENTS_LOG_INGEST_USER_RATE_LIMIT_COUNT", 180)))
    window_seconds = max(1, int(getattr(settings, "EVENTS_LOG_INGEST_USER_RATE_LIMIT_WINDOW_SECONDS", 60)))
    configured_backend = _configured_ingest_backend()
    if configured_backend == "redis":
        try:
            store = _get_redis_ingest_guard_store()
            allowed, retry_after = store.allow_and_record_sliding_window(
                key=f"core-loop:{user_id}",
                limit_count=limit_count,
                window_seconds=window_seconds,
            )
            _set_ingest_guard_state(
                configured_backend="redis",
                active_backend="redis",
                redis_degraded_mode=False,
            )
            if not allowed:
                events_runtime_metrics.record_ingest_blocked(
                    event_name=event_name,
                    reason="rate_limited",
                )
            return bool(allowed), max(0, int(retry_after or 0))
        except Exception as exc:
            _set_ingest_guard_state(
                configured_backend="redis",
                active_backend="memory",
                redis_degraded_mode=True,
            )
            events_runtime_metrics.increment("events_ingest_guard_redis_unavailable_total")
            logger.warning(
                "core_loop_ingest_guard_redis_unavailable reason=%s",
                type(exc).__name__,
            )

    _set_ingest_guard_state(
        configured_backend=configured_backend,
        active_backend="memory",
        redis_degraded_mode=(configured_backend == "redis"),
    )
    now = utcnow()
    key = str(user_id)
    cutoff = now - timedelta(seconds=window_seconds)

    with _INGEST_GUARD_LOCK:
        hits = _INGEST_GUARD_HITS.get(key)
        if hits is None:
            hits = deque()
            _INGEST_GUARD_HITS[key] = hits
        while hits and hits[0] < cutoff:
            hits.popleft()
        if len(hits) >= limit_count:
            oldest = hits[0] if hits else now
            retry_after = max(
                1,
                int((oldest + timedelta(seconds=window_seconds) - now).total_seconds()),
            )
            events_runtime_metrics.record_ingest_blocked(
                event_name=event_name,
                reason="rate_limited",
            )
            return False, retry_after
        hits.append(now)
        return True, 0


def reset_core_loop_ingest_guard_for_tests() -> None:
    global _INGEST_GUARD_REDIS_STORE
    global _INGEST_GUARD_REDIS_INIT_FAILED
    with _INGEST_GUARD_LOCK:
        _INGEST_GUARD_HITS.clear()
    with _INGEST_GUARD_STATE_LOCK:
        _INGEST_GUARD_STATE.clear()
        _INGEST_GUARD_STATE.update(
            {
                "configured_backend": "memory",
                "active_backend": "memory",
                "redis_degraded_mode": False,
            }
        )
        _INGEST_GUARD_REDIS_STORE = None
        _INGEST_GUARD_REDIS_INIT_FAILED = False


def record_core_loop_event(
    *,
    session: Session,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
    event_name: str,
    event_id: str,
    source: str = "web",
    session_id: str | None = None,
    device_id: str | None = None,
    occurred_at: datetime | None = None,
    props: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    privacy: dict[str, Any] | None = None,
) -> CoreLoopRecordResult:
    events_runtime_metrics.record_ingest_attempt(event_name=event_name)
    sanitized_props, props_blocked, props_dropped = _sanitize_payload_with_policy(
        raw_payload=props,
        allowed_keys=_ALLOWED_PROPS_KEYS,
    )
    sanitized_context, context_blocked, context_dropped = _sanitize_payload_with_policy(
        raw_payload=context,
        allowed_keys=_ALLOWED_CONTEXT_KEYS,
    )
    sanitized_privacy, privacy_blocked, privacy_dropped = _sanitize_payload_with_policy(
        raw_payload=privacy,
        allowed_keys=_ALLOWED_PRIVACY_KEYS,
    )
    if "event_schema_version" not in sanitized_context:
        sanitized_context["event_schema_version"] = "v1"

    events_runtime_metrics.record_sanitize(
        blocked_keys=props_blocked + context_blocked + privacy_blocked,
        dropped_items=props_dropped + context_dropped + privacy_dropped,
        oversized_payloads=0,
    )

    dedupe_key = _build_dedupe_key(
        user_id=user_id,
        event_name=event_name,
        event_id=event_id,
    )
    props_json, props_oversized = _serialize_json_payload(sanitized_props)
    context_json, context_oversized = _serialize_json_payload(sanitized_context)
    privacy_json, privacy_oversized = _serialize_json_payload(sanitized_privacy)
    oversized_count = int(props_oversized) + int(context_oversized) + int(privacy_oversized)
    total_payload_bytes = sum(
        len((payload_value or "").encode("utf-8"))
        for payload_value in (props_json, context_json, privacy_json)
    )
    if total_payload_bytes > _json_total_max_bytes():
        props_json = None
        context_json = None
        privacy_json = None
        oversized_count += 1
        events_runtime_metrics.increment("events_ingest_total_json_budget_drop_total")
    if oversized_count:
        events_runtime_metrics.record_sanitize(
            blocked_keys=0,
            dropped_items=0,
            oversized_payloads=oversized_count,
        )

    now = utcnow()
    row = EventsLog(
        ts=occurred_at or now,
        created_at=now,
        updated_at=now,
        user_id=user_id,
        partner_user_id=partner_user_id,
        event_name=event_name,
        event_id=event_id.strip(),
        source=(source or "web").strip()[:64] or "web",
        session_id=(session_id or "").strip()[:128] or None,
        device_id=(device_id or "").strip()[:128] or None,
        props_json=props_json,
        context_json=context_json,
        privacy_json=privacy_json,
        dedupe_key=dedupe_key,
    )

    try:
        with session.begin_nested():
            session.add(row)
            session.flush()
    except IntegrityError:
        logger.info(
            "core_loop_event_deduped_race event_name=%s source=%s",
            event_name,
            source,
        )
        events_runtime_metrics.record_ingest_result(event_name=event_name, deduped=True)
        return CoreLoopRecordResult(accepted=True, deduped=True)

    logger.info(
        "core_loop_event_recorded event_name=%s source=%s user_id=%s partner_user_id=%s",
        event_name,
        source,
        user_id,
        partner_user_id or "-",
    )
    events_runtime_metrics.record_ingest_result(event_name=event_name, deduped=False)
    return CoreLoopRecordResult(accepted=True, deduped=False)


def ensure_daily_loop_completed_for_today(
    *,
    session: Session,
    user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> bool:
    now = utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    rows = session.exec(
        select(EventsLog.event_name).where(
            and_(
                EventsLog.user_id == user_id,
                EventsLog.ts >= day_start,
                EventsLog.ts < day_end,
                EventsLog.event_name.in_(
                    tuple(_DAILY_LOOP_REQUIRED_EVENTS | {_DAILY_LOOP_COMPLETED_EVENT})
                ),
            )
        )
    ).all()
    existing_names = {str(name) for name in rows}
    if _DAILY_LOOP_COMPLETED_EVENT in existing_names:
        return True
    if not _DAILY_LOOP_REQUIRED_EVENTS.issubset(existing_names):
        return False

    event_id = f"auto-loop:{day_start.date().isoformat()}"
    completion_result = record_core_loop_event(
        session=session,
        user_id=user_id,
        partner_user_id=partner_user_id,
        event_name=_DAILY_LOOP_COMPLETED_EVENT,
        event_id=event_id,
        source="server",
        occurred_at=now,
        props={"auto_generated": True, "completion_version": "v1"},
    )
    return bool(completion_result.accepted)
