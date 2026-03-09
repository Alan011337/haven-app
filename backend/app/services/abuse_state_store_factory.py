from __future__ import annotations

import logging
from threading import Lock

from app.core.config import settings
from app.services.abuse_state_store import AbuseStateStore, InMemoryAbuseStateStore, RedisAbuseStateStore

logger = logging.getLogger(__name__)

_memory_store_lock = Lock()
_memory_store_by_scope: dict[str, InMemoryAbuseStateStore] = {}


def _get_or_create_memory_store(scope: str) -> InMemoryAbuseStateStore:
    with _memory_store_lock:
        store = _memory_store_by_scope.get(scope)
        if store is None:
            store = InMemoryAbuseStateStore()
            _memory_store_by_scope[scope] = store
        return store


def create_abuse_state_store(*, scope: str) -> AbuseStateStore:
    backend = (settings.ABUSE_GUARD_STORE_BACKEND or "memory").strip().lower()
    if backend == "redis":
        redis_url = (settings.ABUSE_GUARD_REDIS_URL or "").strip()
        if not redis_url:
            logger.warning(
                "ABUSE_GUARD_STORE_BACKEND=redis but ABUSE_GUARD_REDIS_URL is empty. "
                "Falling back to in-memory store for scope=%s.",
                scope,
            )
            return _get_or_create_memory_store(scope)

        try:
            return RedisAbuseStateStore(
                redis_url=redis_url,
                key_prefix=f"{settings.ABUSE_GUARD_REDIS_KEY_PREFIX}:{scope}:",
            )
        except Exception as exc:
            logger.warning(
                "Failed to initialize Redis abuse state store for scope=%s (reason=%s). "
                "Falling back to in-memory store.",
                scope,
                type(exc).__name__,
            )
            return _get_or_create_memory_store(scope)

    if backend != "memory":
        logger.warning(
            "Unknown ABUSE_GUARD_STORE_BACKEND=%s. Falling back to in-memory store for scope=%s.",
            backend,
            scope,
        )

    return _get_or_create_memory_store(scope)
