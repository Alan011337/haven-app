from __future__ import annotations

import time
from dataclasses import dataclass
from threading import Lock
from typing import Optional

from app.core.config import settings


@dataclass(frozen=True)
class _Entry:
    value: str
    expires_at: float


class WsTypingSessionCache:
    def __init__(self, *, ttl_seconds: float = 8.0, max_entries: int = 2048) -> None:
        self._ttl_seconds = max(0.001, float(ttl_seconds))
        self._max_entries = max(1, int(max_entries))
        self._lock = Lock()
        self._rows: dict[str, _Entry] = {}

    def _now(self) -> float:
        return time.monotonic()

    def _prune(self, *, now: float) -> None:
        stale = [key for key, entry in self._rows.items() if entry.expires_at <= now]
        for key in stale:
            self._rows.pop(key, None)
        if len(self._rows) <= self._max_entries:
            return
        overflow = len(self._rows) - self._max_entries
        for key in list(self._rows.keys())[:overflow]:
            self._rows.pop(key, None)

    def build_key(
        self,
        *,
        sender_user_id: str,
        partner_user_id: str,
        raw_session_id: object,
    ) -> str:
        normalized_raw = str(raw_session_id or "").strip().lower()
        return f"{sender_user_id}:{partner_user_id}:{normalized_raw}"

    def get(self, key: str) -> Optional[str]:
        now = self._now()
        with self._lock:
            entry = self._rows.get(key)
            if not entry:
                return None
            if entry.expires_at <= now:
                self._rows.pop(key, None)
                return None
            return entry.value

    def set(self, key: str, value: str) -> None:
        now = self._now()
        with self._lock:
            self._prune(now=now)
            self._rows[key] = _Entry(value=value, expires_at=now + self._ttl_seconds)
            self._prune(now=now)


ws_typing_session_cache = WsTypingSessionCache(
    ttl_seconds=float(getattr(settings, "WS_TYPING_SESSION_CACHE_TTL_SECONDS", 8.0) or 8.0),
    max_entries=int(getattr(settings, "WS_TYPING_SESSION_CACHE_MAX_ENTRIES", 2048) or 2048),
)
