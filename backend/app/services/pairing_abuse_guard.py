from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Callable, Deque, Optional

from app.core.datetime_utils import utcnow
from app.services.abuse_state_store import AbuseStateStore


@dataclass
class _PairingState:
    attempts: Deque[datetime] = field(default_factory=deque)
    consecutive_failures: int = 0
    blocked_until: Optional[datetime] = None


class PairingAbuseGuard:
    def __init__(
        self,
        *,
        limit_count: int,
        window_seconds: int,
        failure_threshold: int,
        cooldown_seconds: int,
        cleanup_interval_seconds: int = 60,
        now_fn: Optional[Callable[[], datetime]] = None,
        state_store: Optional[AbuseStateStore] = None,
    ) -> None:
        self.limit_count = max(1, int(limit_count))
        self.window_seconds = max(1, int(window_seconds))
        self.failure_threshold = max(1, int(failure_threshold))
        self.cooldown_seconds = max(1, int(cooldown_seconds))
        self.cleanup_interval_seconds = max(1, int(cleanup_interval_seconds))
        self._now_fn = now_fn or utcnow
        self._state_store = state_store
        self._store_ttl_seconds = (
            max(self.window_seconds, self.cooldown_seconds) + self.cleanup_interval_seconds
        )
        self._lock = Lock()
        self._states: dict[str, _PairingState] = {}
        self._next_cleanup_at: Optional[datetime] = None

    @staticmethod
    def _parse_datetime(raw_value: Any) -> Optional[datetime]:
        if not isinstance(raw_value, str):
            return None
        try:
            parsed = datetime.fromisoformat(raw_value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=utcnow().tzinfo)

    def _serialize_state(self, state: _PairingState) -> dict[str, Any]:
        return {
            "attempts": [item.isoformat() for item in state.attempts],
            "consecutive_failures": int(max(0, state.consecutive_failures)),
            "blocked_until": state.blocked_until.isoformat() if state.blocked_until else None,
        }

    def _deserialize_state(self, payload: dict[str, Any]) -> _PairingState:
        raw_attempts = payload.get("attempts", [])
        attempts: Deque[datetime] = deque()
        if isinstance(raw_attempts, list):
            for raw_item in raw_attempts:
                parsed = self._parse_datetime(raw_item)
                if parsed:
                    attempts.append(parsed)

        blocked_until = self._parse_datetime(payload.get("blocked_until"))
        consecutive_failures = payload.get("consecutive_failures", 0)
        if not isinstance(consecutive_failures, int):
            consecutive_failures = 0

        return _PairingState(
            attempts=attempts,
            consecutive_failures=max(0, consecutive_failures),
            blocked_until=blocked_until,
        )

    def _load_state(self, *, key: str) -> Optional[_PairingState]:
        if self._state_store is None:
            return self._states.get(key)

        payload = self._state_store.load(key)
        if payload is None:
            return None
        return self._deserialize_state(payload)

    def _save_state(self, *, key: str, state: _PairingState) -> None:
        if self._state_store is None:
            self._states[key] = state
            return
        self._state_store.save(
            key,
            self._serialize_state(state),
            ttl_seconds=self._store_ttl_seconds,
        )

    def _delete_state(self, *, key: str) -> None:
        if self._state_store is None:
            self._states.pop(key, None)
            return
        self._state_store.delete(key)

    def _iter_state_items(self) -> list[tuple[str, _PairingState]]:
        if self._state_store is None:
            return list(self._states.items())

        items: list[tuple[str, _PairingState]] = []
        for key in self._state_store.iter_keys():
            state = self._load_state(key=key)
            if state is None:
                continue
            items.append((key, state))
        return items

    def _load_or_create_state(self, *, key: str) -> _PairingState:
        state = self._load_state(key=key)
        if state is not None:
            return state

        created = _PairingState()
        self._save_state(key=key, state=created)
        return created

    def _prune_attempts(self, state: _PairingState, *, now: datetime) -> None:
        window_start = now - timedelta(seconds=self.window_seconds)
        while state.attempts and state.attempts[0] < window_start:
            state.attempts.popleft()

    def _is_state_idle(self, state: _PairingState, *, now: datetime) -> bool:
        return (not state.attempts) and (state.blocked_until is None or state.blocked_until <= now)

    def _maybe_cleanup(self, *, now: datetime) -> None:
        if self._next_cleanup_at and now < self._next_cleanup_at:
            return
        if self._state_store is not None and not getattr(
            self._state_store, "supports_global_cleanup_scan", True
        ):
            self._next_cleanup_at = now + timedelta(seconds=self.cleanup_interval_seconds)
            return

        for key, state in self._iter_state_items():
            self._prune_attempts(state, now=now)
            if self._is_state_idle(state, now=now):
                self._delete_state(key=key)
                continue
            self._save_state(key=key, state=state)

        self._next_cleanup_at = now + timedelta(seconds=self.cleanup_interval_seconds)

    def allow_attempt(self, *, key: str) -> tuple[bool, Optional[str], int]:
        now = self._now_fn()
        with self._lock:
            self._maybe_cleanup(now=now)
            state = self._load_or_create_state(key=key)
            self._prune_attempts(state, now=now)
            self._save_state(key=key, state=state)

            if state.blocked_until and now < state.blocked_until:
                retry_after = max(1, int((state.blocked_until - now).total_seconds()))
                return False, "cooldown_active", retry_after

            if len(state.attempts) >= self.limit_count:
                retry_after = max(
                    1,
                    int((state.attempts[0] + timedelta(seconds=self.window_seconds) - now).total_seconds()),
                )
                return False, "rate_limited", retry_after

            return True, None, 0

    def record_attempt(self, *, key: str, success: bool) -> None:
        now = self._now_fn()
        with self._lock:
            self._maybe_cleanup(now=now)
            state = self._load_or_create_state(key=key)
            self._prune_attempts(state, now=now)
            state.attempts.append(now)

            if success:
                state.consecutive_failures = 0
                state.blocked_until = None
                self._save_state(key=key, state=state)
                return

            state.consecutive_failures += 1
            if state.consecutive_failures >= self.failure_threshold:
                state.blocked_until = now + timedelta(seconds=self.cooldown_seconds)
                state.consecutive_failures = 0
            self._save_state(key=key, state=state)

    def reset(self) -> None:
        with self._lock:
            if self._state_store is None:
                self._states.clear()
            else:
                for key in self._state_store.iter_keys():
                    self._state_store.delete(key)
            self._next_cleanup_at = None

    def tracked_key_count(self) -> int:
        with self._lock:
            if self._state_store is None:
                return len(self._states)
            return len(list(self._state_store.iter_keys()))
