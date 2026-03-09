from __future__ import annotations

import logging
import time
from math import ceil
from threading import Lock
from typing import Any, Callable, Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationDedupeStore(Protocol):
    def reserve(self, *, dedupe_key: str, cooldown_seconds: float) -> bool:
        ...

    def release(self, *, dedupe_key: str) -> None:
        ...

    def reset(self) -> None:
        ...


class InMemoryNotificationDedupeStore:
    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._dedupe_until: dict[str, float] = {}

    def reserve(self, *, dedupe_key: str, cooldown_seconds: float) -> bool:
        if cooldown_seconds <= 0:
            return True

        now = self._clock()
        with self._lock:
            cooldown_until = self._dedupe_until.get(dedupe_key, 0.0)
            if cooldown_until > now:
                return False

            self._dedupe_until[dedupe_key] = now + cooldown_seconds

            # Best-effort cleanup to avoid unbounded map growth.
            if len(self._dedupe_until) > 5000:
                expired = [key for key, until in self._dedupe_until.items() if until <= now]
                for key in expired:
                    self._dedupe_until.pop(key, None)

        return True

    def release(self, *, dedupe_key: str) -> None:
        with self._lock:
            self._dedupe_until.pop(dedupe_key, None)

    def reset(self) -> None:
        with self._lock:
            self._dedupe_until.clear()


class RedisNotificationDedupeStore:
    def __init__(self, *, redis_url: str, key_prefix: str, client: Any | None = None) -> None:
        if client is None:
            try:
                import redis
            except Exception as exc:  # pragma: no cover
                raise RuntimeError(
                    "Redis notification dedupe store requires the 'redis' package."
                ) from exc
            client = redis.Redis.from_url(redis_url, decode_responses=True)

        self._client = client
        self._key_prefix = key_prefix
        self._fallback = InMemoryNotificationDedupeStore()
        self._fallback_enabled = False
        self._fallback_lock = Lock()

    def _full_key(self, dedupe_key: str) -> str:
        return f"{self._key_prefix}:{dedupe_key}"

    def _enable_fallback(self, *, reason: Exception) -> None:
        with self._fallback_lock:
            if self._fallback_enabled:
                return
            self._fallback_enabled = True
            logger.warning(
                "Redis notification dedupe store unavailable (reason=%s). "
                "Falling back to in-memory dedupe store for this process.",
                type(reason).__name__,
            )

    def reserve(self, *, dedupe_key: str, cooldown_seconds: float) -> bool:
        if cooldown_seconds <= 0:
            return True
        if self._fallback_enabled:
            return self._fallback.reserve(
                dedupe_key=dedupe_key,
                cooldown_seconds=cooldown_seconds,
            )
        ttl_seconds = max(1, int(ceil(cooldown_seconds)))
        try:
            reserved = self._client.set(
                self._full_key(dedupe_key),
                "1",
                nx=True,
                ex=ttl_seconds,
            )
            return bool(reserved)
        except Exception as exc:
            self._enable_fallback(reason=exc)
            return self._fallback.reserve(
                dedupe_key=dedupe_key,
                cooldown_seconds=cooldown_seconds,
            )

    def release(self, *, dedupe_key: str) -> None:
        if self._fallback_enabled:
            self._fallback.release(dedupe_key=dedupe_key)
            return
        try:
            self._client.delete(self._full_key(dedupe_key))
        except Exception as exc:
            self._enable_fallback(reason=exc)
            self._fallback.release(dedupe_key=dedupe_key)

    def reset(self) -> None:
        if self._fallback_enabled:
            self._fallback.reset()
            return
        pattern = f"{self._key_prefix}:*"
        try:
            for full_key in self._client.scan_iter(match=pattern):
                self._client.delete(full_key)
        except Exception as exc:
            self._enable_fallback(reason=exc)
            self._fallback.reset()


def create_notification_dedupe_store() -> NotificationDedupeStore:
    backend = (settings.ABUSE_GUARD_STORE_BACKEND or "memory").strip().lower()
    if backend == "redis":
        redis_url = (settings.ABUSE_GUARD_REDIS_URL or "").strip()
        if redis_url:
            try:
                return RedisNotificationDedupeStore(
                    redis_url=redis_url,
                    key_prefix=f"{settings.ABUSE_GUARD_REDIS_KEY_PREFIX}:notification:dedupe",
                )
            except Exception as exc:
                logger.warning(
                    "Failed to initialize Redis notification dedupe store (reason=%s). "
                    "Falling back to in-memory store.",
                    type(exc).__name__,
                )
        else:
            logger.warning(
                "ABUSE_GUARD_STORE_BACKEND=redis but ABUSE_GUARD_REDIS_URL is empty. "
                "Using in-memory notification dedupe store."
            )

    if backend != "memory":
        logger.warning(
            "Unknown ABUSE_GUARD_STORE_BACKEND=%s for notification dedupe. "
            "Using in-memory store.",
            backend,
        )

    return InMemoryNotificationDedupeStore()
