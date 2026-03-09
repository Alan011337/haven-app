from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
import logging
from threading import Lock
from typing import Any, Deque
from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, func, select

from app.core.log_redaction import redact_ip
from app.core.datetime_utils import utcnow
from app.models.card_response import CardResponse
from app.models.journal import Journal
from app.services.abuse_state_store import AbuseStateStore, InMemoryAbuseStateStore
from app.services.abuse_state_store_factory import create_abuse_state_store
from app.services.rate_limit_runtime_metrics import rate_limit_runtime_metrics
from app.services.rate_limit_scope import (
    build_partner_pair_scope,
    build_rate_limit_scope_key,
    normalize_scope_component,
)

logger = logging.getLogger(__name__)


class _SlidingWindowScopeLimiter:
    def __init__(
        self,
        *,
        state_store: AbuseStateStore | None = None,
        cleanup_interval_seconds: int = 60,
    ) -> None:
        self._state_store = state_store
        self._cleanup_interval_seconds = max(1, int(cleanup_interval_seconds))
        self._lock = Lock()
        self._fallback_hits: dict[str, Deque[datetime]] = {}
        self._store_degraded = False

    @staticmethod
    def _parse_datetime(raw_value: Any) -> datetime | None:
        if not isinstance(raw_value, str):
            return None
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utcnow().tzinfo)

    def _serialize_hits(self, hits: Deque[datetime]) -> dict[str, Any]:
        return {"hits": [item.isoformat() for item in hits]}

    def _deserialize_hits(self, payload: dict[str, Any]) -> Deque[datetime]:
        raw_hits = payload.get("hits", [])
        hits: Deque[datetime] = deque()
        if isinstance(raw_hits, list):
            for raw_item in raw_hits:
                parsed = self._parse_datetime(raw_item)
                if parsed:
                    hits.append(parsed)
        return hits

    def _load_hits(self, *, key: str) -> Deque[datetime]:
        if self._state_store is None or self._store_degraded:
            return self._fallback_hits.get(key, deque())
        try:
            payload = self._state_store.load(key)
        except Exception as exc:
            logger.warning(
                "Rate limit store read failed; downgrade to memory: reason=%s",
                type(exc).__name__,
            )
            self._store_degraded = True
            return self._fallback_hits.get(key, deque())
        if payload is None:
            return deque()
        return self._deserialize_hits(payload)

    def _save_hits(self, *, key: str, hits: Deque[datetime], window_seconds: int) -> None:
        if self._state_store is None or self._store_degraded:
            if hits:
                self._fallback_hits[key] = deque(hits)
            else:
                self._fallback_hits.pop(key, None)
            return
        try:
            if not hits:
                self._state_store.delete(key)
                return
            ttl_seconds = max(1, int(window_seconds)) + self._cleanup_interval_seconds
            self._state_store.save(
                key,
                self._serialize_hits(hits),
                ttl_seconds=ttl_seconds,
            )
        except Exception as exc:
            logger.warning(
                "Rate limit store write failed; downgrade to memory: reason=%s",
                type(exc).__name__,
            )
            self._store_degraded = True
            if hits:
                self._fallback_hits[key] = deque(hits)
            else:
                self._fallback_hits.pop(key, None)

    def allow_and_record(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        if limit_count <= 0:
            return True, 0

        safe_window_seconds = max(1, int(window_seconds))
        safe_limit_count = max(1, int(limit_count))

        if self._state_store is not None and not self._store_degraded:
            atomic_allow_and_record = getattr(self._state_store, "allow_and_record_sliding_window", None)
            if callable(atomic_allow_and_record):
                try:
                    return atomic_allow_and_record(
                        key=key,
                        limit_count=safe_limit_count,
                        window_seconds=safe_window_seconds,
                    )
                except Exception as exc:
                    logger.warning(
                        "Rate limit atomic store failed; downgrade to memory: reason=%s",
                        type(exc).__name__,
                    )
                    self._store_degraded = True

        cutoff = utcnow() - timedelta(seconds=safe_window_seconds)

        with self._lock:
            hits = self._load_hits(key=key)
            while hits and hits[0] < cutoff:
                hits.popleft()

            if len(hits) >= safe_limit_count:
                retry_after_seconds = int(
                    (hits[0] + timedelta(seconds=safe_window_seconds) - utcnow()).total_seconds()
                )
                self._save_hits(key=key, hits=hits, window_seconds=safe_window_seconds)
                return False, max(1, retry_after_seconds)

            hits.append(utcnow())
            self._save_hits(key=key, hits=hits, window_seconds=safe_window_seconds)
            return True, 0


_journal_ip_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="journal-rate-limit-ip")
)
_journal_device_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="journal-rate-limit-device")
)
_journal_partner_pair_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="journal-rate-limit-partner-pair")
)
_card_ip_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="card-rate-limit-ip")
)
_card_device_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="card-rate-limit-device")
)
_card_partner_pair_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="card-rate-limit-partner-pair")
)

# Login brute-force protection (IP-based)
_login_ip_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="login-rate-limit-ip")
)

# Registration abuse protection (IP-based)
_registration_ip_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="registration-rate-limit-ip")
)
_ws_connection_scope_limiter = _SlidingWindowScopeLimiter(
    state_store=create_abuse_state_store(scope="ws-connection-rate-limit")
)


def reset_rate_limit_state_for_tests() -> None:
    """
    Reset in-memory limiter state for deterministic tests.

    This helper is intentionally test-facing and should not be used in runtime flows.
    """
    limiters = (
        _journal_ip_scope_limiter,
        _journal_device_scope_limiter,
        _journal_partner_pair_scope_limiter,
        _card_ip_scope_limiter,
        _card_device_scope_limiter,
        _card_partner_pair_scope_limiter,
        _login_ip_scope_limiter,
        _registration_ip_scope_limiter,
        _ws_connection_scope_limiter,
    )
    for limiter in limiters:
        with limiter._lock:
            limiter._state_store = InMemoryAbuseStateStore()
            limiter._fallback_hits.clear()
            limiter._store_degraded = False


def enforce_login_rate_limit(
    *,
    client_ip: str | None,
    ip_limit_count: int,
    ip_window_seconds: int,
) -> None:
    """
    Enforce IP-based rate limiting on the login endpoint.

    Raises HTTP 429 if the same IP exceeds *ip_limit_count* login
    attempts within *ip_window_seconds*.
    """
    if not client_ip or ip_limit_count <= 0:
        return

    rate_limit_runtime_metrics.record_attempt(
        action="login",
        scope="ip",
        endpoint="/api/auth/token",
    )
    allowed, retry_after = _login_ip_scope_limiter.allow_and_record(
        key=client_ip,
        limit_count=ip_limit_count,
        window_seconds=ip_window_seconds,
    )
    if not allowed:
        rate_limit_runtime_metrics.record_blocked(
            action="login",
            scope="ip",
            endpoint="/api/auth/token",
        )
        redacted_ip = redact_ip(client_ip)
        logger.warning(
            "Login rate-limited IP=%s (retry_after=%ss)",
            redacted_ip,
            retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="登入嘗試次數過多，請稍後再試。",
            headers={"Retry-After": str(retry_after)},
        )


def enforce_registration_rate_limit(
    *,
    client_ip: str | None,
    ip_limit_count: int,
    ip_window_seconds: int,
) -> None:
    """
    Enforce IP-based rate limiting on the registration endpoint.

    Raises HTTP 429 if the same IP exceeds *ip_limit_count* registration
    attempts within *ip_window_seconds*.
    """
    if not client_ip or ip_limit_count <= 0:
        return

    rate_limit_runtime_metrics.record_attempt(
        action="registration",
        scope="ip",
        endpoint="/api/users/",
    )
    allowed, retry_after = _registration_ip_scope_limiter.allow_and_record(
        key=client_ip,
        limit_count=ip_limit_count,
        window_seconds=ip_window_seconds,
    )
    if not allowed:
        rate_limit_runtime_metrics.record_blocked(
            action="registration",
            scope="ip",
            endpoint="/api/users/",
        )
        redacted_ip = redact_ip(client_ip)
        logger.warning(
            "Registration rate-limited IP=%s (retry_after=%ss)",
            redacted_ip,
            retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="註冊嘗試次數過多，請稍後再試。",
            headers={"Retry-After": str(retry_after)},
        )


def _resolve_rate_limit_window_start(window_seconds: int) -> datetime:
    safe_window_seconds = max(1, int(window_seconds))
    return utcnow() - timedelta(seconds=safe_window_seconds)


def _resolve_retry_after_seconds(
    *,
    oldest_created_at: datetime | None,
    window_seconds: int,
) -> int:
    safe_window_seconds = max(1, int(window_seconds))
    if oldest_created_at is None:
        return safe_window_seconds

    reset_at = oldest_created_at + timedelta(seconds=safe_window_seconds)
    remaining = int((reset_at - utcnow()).total_seconds())
    return max(1, remaining)


def _log_rate_limit_block(
    *,
    endpoint: str,
    action: str,
    scope: str,
    user_id: UUID,
    partner_id: UUID | None,
    retry_after_seconds: int,
    limit_count: int,
    window_seconds: int,
) -> None:
    logger.warning(
        (
            "rate_limit_block endpoint=%s action=%s scope=%s user_id=%s "
            "partner_id=%s retry_after_seconds=%s limit_count=%s window_seconds=%s"
        ),
        endpoint,
        action,
        scope,
        user_id,
        partner_id,
        retry_after_seconds,
        limit_count,
        window_seconds,
    )


def _raise_rate_limited(
    detail: str,
    *,
    retry_after_seconds: int,
    scope: str,
    action: str,
    endpoint: str,
    user_id: UUID,
    partner_id: UUID | None,
    limit_count: int,
    window_seconds: int,
) -> None:
    rate_limit_runtime_metrics.record_blocked(
        scope=scope,
        action=action,
        endpoint=endpoint,
    )
    _log_rate_limit_block(
        endpoint=endpoint,
        action=action,
        scope=scope,
        user_id=user_id,
        partner_id=partner_id,
        retry_after_seconds=retry_after_seconds,
        limit_count=limit_count,
        window_seconds=window_seconds,
    )
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={
            "Retry-After": str(max(1, int(retry_after_seconds))),
            "X-RateLimit-Scope": scope,
            "X-RateLimit-Action": action,
        },
    )


def _normalize_scope_key_part(raw_value: str) -> str:
    return normalize_scope_component(raw_value, fallback="unknown")


def _resolve_partner_pair_scope_key(*, user_id: UUID, partner_id: UUID | None) -> str:
    return build_partner_pair_scope(user_id=user_id, partner_id=partner_id)


def _enforce_scope_limit(
    *,
    limiter: _SlidingWindowScopeLimiter,
    key: str | None,
    limit_count: int,
    window_seconds: int,
    detail: str,
    scope: str,
    action: str,
    endpoint: str,
    user_id: UUID,
    partner_id: UUID | None,
) -> None:
    if not key or limit_count <= 0:
        return

    rate_limit_runtime_metrics.record_attempt(
        scope=scope,
        action=action,
        endpoint=endpoint,
    )
    allowed, retry_after_seconds = limiter.allow_and_record(
        key=key,
        limit_count=limit_count,
        window_seconds=window_seconds,
    )
    if allowed:
        return
    _raise_rate_limited(
        detail,
        retry_after_seconds=retry_after_seconds,
        scope=scope,
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
        limit_count=limit_count,
        window_seconds=window_seconds,
    )


def enforce_journal_create_rate_limit(
    *,
    session: Session,
    user_id: UUID,
    limit_count: int,
    window_seconds: int,
    partner_id: UUID | None = None,
    client_ip: str | None = None,
    device_id: str | None = None,
    ip_limit_count: int = 0,
    device_limit_count: int = 0,
    partner_pair_limit_count: int = 0,
    endpoint: str = "/api/journals/",
) -> None:
    action = "journal_create"
    if limit_count > 0:
        rate_limit_runtime_metrics.record_attempt(
            scope="user",
            action=action,
            endpoint=endpoint,
        )
        window_start = _resolve_rate_limit_window_start(window_seconds)
        recent_count = int(
            session.exec(
                select(func.count(Journal.id)).where(
                    Journal.user_id == user_id,
                    Journal.created_at >= window_start,
                )
            ).one()
            or 0
        )
        if recent_count >= limit_count:
            oldest_in_window = session.exec(
                select(func.min(Journal.created_at)).where(
                    Journal.user_id == user_id,
                    Journal.created_at >= window_start,
                )
            ).one()
            retry_after_seconds = _resolve_retry_after_seconds(
                oldest_created_at=oldest_in_window,
                window_seconds=window_seconds,
            )
            _raise_rate_limited(
                "日記提交過於頻繁，請稍後再試。",
                retry_after_seconds=retry_after_seconds,
                scope="user",
                action=action,
                endpoint=endpoint,
                user_id=user_id,
                partner_id=partner_id,
                limit_count=limit_count,
                window_seconds=window_seconds,
            )

    normalized_ip = _normalize_scope_key_part(client_ip or "unknown")
    pair_scope_key = _resolve_partner_pair_scope_key(user_id=user_id, partner_id=partner_id)
    normalized_device_id = _normalize_scope_key_part(device_id) if device_id else None

    _enforce_scope_limit(
        limiter=_journal_ip_scope_limiter,
        key=build_rate_limit_scope_key(domain="journal", scope="ip", value=normalized_ip),
        limit_count=ip_limit_count,
        window_seconds=window_seconds,
        detail="日記提交過於頻繁，請稍後再試。",
        scope="ip",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )
    _enforce_scope_limit(
        limiter=_journal_device_scope_limiter,
        key=(
            build_rate_limit_scope_key(
                domain="journal",
                scope="device",
                value=normalized_device_id,
            )
            if normalized_device_id
            else None
        ),
        limit_count=device_limit_count,
        window_seconds=window_seconds,
        detail="日記提交過於頻繁，請稍後再試。",
        scope="device",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )
    _enforce_scope_limit(
        limiter=_journal_partner_pair_scope_limiter,
        key=build_rate_limit_scope_key(domain="journal", scope="pair", value=pair_scope_key),
        limit_count=partner_pair_limit_count,
        window_seconds=window_seconds,
        detail="日記提交過於頻繁，請稍後再試。",
        scope="partner_pair",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )


def enforce_card_response_create_rate_limit(
    *,
    session: Session,
    user_id: UUID,
    limit_count: int,
    window_seconds: int,
    partner_id: UUID | None = None,
    client_ip: str | None = None,
    device_id: str | None = None,
    ip_limit_count: int = 0,
    device_limit_count: int = 0,
    partner_pair_limit_count: int = 0,
    endpoint: str = "/api/cards/respond",
) -> None:
    action = "card_response_create"
    if limit_count > 0:
        rate_limit_runtime_metrics.record_attempt(
            scope="user",
            action=action,
            endpoint=endpoint,
        )
        window_start = _resolve_rate_limit_window_start(window_seconds)
        recent_count = int(
            session.exec(
                select(func.count(CardResponse.id)).where(
                    CardResponse.user_id == user_id,
                    CardResponse.created_at >= window_start,
                )
            ).one()
            or 0
        )
        if recent_count >= limit_count:
            oldest_in_window = session.exec(
                select(func.min(CardResponse.created_at)).where(
                    CardResponse.user_id == user_id,
                    CardResponse.created_at >= window_start,
                )
            ).one()
            retry_after_seconds = _resolve_retry_after_seconds(
                oldest_created_at=oldest_in_window,
                window_seconds=window_seconds,
            )
            _raise_rate_limited(
                "卡片回答過於頻繁，請稍後再試。",
                retry_after_seconds=retry_after_seconds,
                scope="user",
                action=action,
                endpoint=endpoint,
                user_id=user_id,
                partner_id=partner_id,
                limit_count=limit_count,
                window_seconds=window_seconds,
            )

    normalized_ip = _normalize_scope_key_part(client_ip or "unknown")
    pair_scope_key = _resolve_partner_pair_scope_key(user_id=user_id, partner_id=partner_id)
    normalized_device_id = _normalize_scope_key_part(device_id) if device_id else None

    _enforce_scope_limit(
        limiter=_card_ip_scope_limiter,
        key=build_rate_limit_scope_key(domain="card", scope="ip", value=normalized_ip),
        limit_count=ip_limit_count,
        window_seconds=window_seconds,
        detail="卡片回答過於頻繁，請稍後再試。",
        scope="ip",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )
    _enforce_scope_limit(
        limiter=_card_device_scope_limiter,
        key=(
            build_rate_limit_scope_key(
                domain="card",
                scope="device",
                value=normalized_device_id,
            )
            if normalized_device_id
            else None
        ),
        limit_count=device_limit_count,
        window_seconds=window_seconds,
        detail="卡片回答過於頻繁，請稍後再試。",
        scope="device",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )
    _enforce_scope_limit(
        limiter=_card_partner_pair_scope_limiter,
        key=build_rate_limit_scope_key(domain="card", scope="pair", value=pair_scope_key),
        limit_count=partner_pair_limit_count,
        window_seconds=window_seconds,
        detail="卡片回答過於頻繁，請稍後再試。",
        scope="partner_pair",
        action=action,
        endpoint=endpoint,
        user_id=user_id,
        partner_id=partner_id,
    )


def check_ws_connection_rate_limit(
    *,
    scope_key: str,
    limit_count: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Return (allowed, retry_after_seconds) for websocket connection attempts.

    This is intentionally non-raising so WebSocket handlers can choose close code
    and payload semantics.
    """
    safe_scope_key = normalize_scope_component(scope_key, fallback="ws")
    if not safe_scope_key or limit_count <= 0:
        return True, 0

    return _ws_connection_scope_limiter.allow_and_record(
        key=build_rate_limit_scope_key(domain="ws", scope="connection", value=safe_scope_key),
        limit_count=limit_count,
        window_seconds=window_seconds,
    )
