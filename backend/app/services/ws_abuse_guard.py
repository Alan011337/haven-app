from __future__ import annotations

from collections import deque
from math import ceil
from threading import Lock
import time
from typing import Any, Callable, Optional

from app.services.abuse_state_store import AbuseStateStore


class WsAbuseGuard:
    """
    Lightweight, in-process WebSocket abuse protection.
    - Connection caps (per-user / global)
    - Message rate limit (rolling window)
    - Temporary backoff after rate-limit violation
    - Max payload size guard
    """

    def __init__(
        self,
        *,
        limit_count: int,
        window_seconds: int,
        backoff_seconds: int,
        max_payload_bytes: int,
        cleanup_interval_seconds: int = 60,
        clock: Callable[[], float] | None = None,
        state_store: Optional[AbuseStateStore] = None,
    ) -> None:
        self.limit_count = max(1, int(limit_count))
        self.window_seconds = max(1, int(window_seconds))
        self.backoff_seconds = max(1, int(backoff_seconds))
        self.max_payload_bytes = max(1, int(max_payload_bytes))
        self.cleanup_interval_seconds = max(1, int(cleanup_interval_seconds))
        self._clock = clock or time.monotonic
        self._state_store = state_store
        self._store_ttl_seconds = (
            max(self.window_seconds, self.backoff_seconds) + self.cleanup_interval_seconds
        )

        self._message_windows: dict[str, deque[float]] = {}
        self._backoff_until: dict[str, float] = {}
        self._lock = Lock()
        self._next_cleanup_at: float = 0.0

    def _serialize_user_state(self, *, window: deque[float], backoff_until: float) -> dict[str, Any]:
        return {
            "window": list(window),
            "backoff_until": float(backoff_until),
        }

    def _deserialize_user_state(self, payload: dict[str, Any]) -> tuple[deque[float], float]:
        raw_window = payload.get("window", [])
        window = deque()
        if isinstance(raw_window, list):
            for item in raw_window:
                try:
                    window.append(float(item))
                except (TypeError, ValueError):
                    continue

        raw_backoff = payload.get("backoff_until", 0.0)
        try:
            backoff_until = float(raw_backoff)
        except (TypeError, ValueError):
            backoff_until = 0.0

        return window, max(0.0, backoff_until)

    def _load_user_state(self, *, user_id: str) -> tuple[deque[float], float]:
        if self._state_store is None:
            window = self._message_windows.setdefault(user_id, deque())
            backoff_until = self._backoff_until.get(user_id, 0.0)
            return window, backoff_until

        payload = self._state_store.load(user_id)
        if payload is None:
            return deque(), 0.0
        return self._deserialize_user_state(payload)

    def _save_user_state(self, *, user_id: str, window: deque[float], backoff_until: float, now: float) -> None:
        if self._state_store is None:
            if window:
                self._message_windows[user_id] = window
            else:
                self._message_windows.pop(user_id, None)

            if backoff_until > now:
                self._backoff_until[user_id] = backoff_until
            else:
                self._backoff_until.pop(user_id, None)
            return

        if not window and backoff_until <= now:
            self._state_store.delete(user_id)
            return

        self._state_store.save(
            user_id,
            self._serialize_user_state(window=window, backoff_until=backoff_until),
            ttl_seconds=self._store_ttl_seconds,
        )

    def _iter_user_ids(self) -> list[str]:
        if self._state_store is None:
            return list(set(self._message_windows.keys()) | set(self._backoff_until.keys()))
        return list(self._state_store.iter_keys())

    def _maybe_cleanup(self, *, now: float) -> None:
        if now < self._next_cleanup_at:
            return
        if self._state_store is not None and not getattr(
            self._state_store, "supports_global_cleanup_scan", True
        ):
            self._next_cleanup_at = now + self.cleanup_interval_seconds
            return

        cutoff = now - self.window_seconds

        for user_id in self._iter_user_ids():
            window, backoff_until = self._load_user_state(user_id=user_id)
            while window and window[0] <= cutoff:
                window.popleft()
            self._save_user_state(user_id=user_id, window=window, backoff_until=backoff_until, now=now)

        self._next_cleanup_at = now + self.cleanup_interval_seconds

    def allow_new_connection(
        self,
        *,
        user_id: str,
        active_user_connections: int,
        active_total_connections: int,
        max_connections_per_user: int,
        max_connections_global: int,
    ) -> tuple[bool, str | None]:
        per_user_cap = max(1, int(max_connections_per_user))
        global_cap = max(1, int(max_connections_global))

        if active_total_connections >= global_cap:
            return False, "global_connection_cap"
        if active_user_connections >= per_user_cap:
            return False, "per_user_connection_cap"
        return True, None

    def apply_runtime_limits(
        self,
        *,
        limit_count: int,
        window_seconds: int,
        backoff_seconds: int,
        max_payload_bytes: int,
    ) -> None:
        """
        Update message abuse limits at runtime.
        This keeps long-lived app processes aligned with dynamic settings changes.
        """
        safe_limit_count = max(1, int(limit_count))
        safe_window_seconds = max(1, int(window_seconds))
        safe_backoff_seconds = max(1, int(backoff_seconds))
        safe_max_payload_bytes = max(1, int(max_payload_bytes))
        with self._lock:
            self.limit_count = safe_limit_count
            self.window_seconds = safe_window_seconds
            self.backoff_seconds = safe_backoff_seconds
            self.max_payload_bytes = safe_max_payload_bytes
            self._store_ttl_seconds = (
                max(self.window_seconds, self.backoff_seconds) + self.cleanup_interval_seconds
            )

    def evaluate_message(
        self,
        *,
        user_id: str,
        payload_text: str,
        scope_key: str | None = None,
    ) -> tuple[bool, dict | None]:
        now = self._clock()
        scope = (scope_key or user_id).strip() or user_id

        payload_size = len(payload_text.encode("utf-8"))
        if payload_size > self.max_payload_bytes:
            return False, {
                "reason": "payload_too_large",
                "retry_after_seconds": self.backoff_seconds,
            }

        with self._lock:
            self._maybe_cleanup(now=now)
            window, backoff_until = self._load_user_state(user_id=scope)
            if backoff_until > now:
                self._save_user_state(user_id=scope, window=window, backoff_until=backoff_until, now=now)
                return False, {
                    "reason": "backoff_active",
                    "retry_after_seconds": max(1, ceil(backoff_until - now)),
                    "scope": scope,
                }

            cutoff = now - self.window_seconds
            while window and window[0] <= cutoff:
                window.popleft()

            if len(window) >= self.limit_count:
                backoff_until = now + self.backoff_seconds
                window.clear()
                self._save_user_state(user_id=scope, window=window, backoff_until=backoff_until, now=now)
                return False, {
                    "reason": "message_rate_limited",
                    "retry_after_seconds": self.backoff_seconds,
                    "scope": scope,
                }

            window.append(now)
            self._save_user_state(user_id=scope, window=window, backoff_until=backoff_until, now=now)
            return True, None

    def tracked_user_count(self) -> int:
        with self._lock:
            return len(self._iter_user_ids())
