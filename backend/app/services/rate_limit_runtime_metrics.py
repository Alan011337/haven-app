from __future__ import annotations

from threading import Lock
from typing import Any


def _sanitize_key_part(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in (raw or "").strip().lower())
    compact = "_".join(part for part in cleaned.split("_") if part)
    return compact[:96] or "unknown"


class RateLimitRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._attempt_total: int = 0
        self._attempt_by_scope: dict[str, int] = {}
        self._attempt_by_action: dict[str, int] = {}
        self._attempt_by_endpoint: dict[str, int] = {}
        self._attempt_by_action_scope: dict[str, int] = {}
        self._blocked_total: int = 0
        self._blocked_by_scope: dict[str, int] = {}
        self._blocked_by_action: dict[str, int] = {}
        self._blocked_by_endpoint: dict[str, int] = {}
        self._blocked_by_action_scope: dict[str, int] = {}

    def record_attempt(
        self,
        *,
        scope: str,
        action: str,
        endpoint: str,
        amount: int = 1,
    ) -> None:
        safe_amount = int(amount)
        if safe_amount <= 0:
            return

        safe_scope = _sanitize_key_part(scope)
        safe_action = _sanitize_key_part(action)
        safe_endpoint = _sanitize_key_part(endpoint)
        safe_action_scope = f"{safe_action}__{safe_scope}"

        with self._lock:
            self._attempt_total += safe_amount
            self._attempt_by_scope[safe_scope] = self._attempt_by_scope.get(safe_scope, 0) + safe_amount
            self._attempt_by_action[safe_action] = (
                self._attempt_by_action.get(safe_action, 0) + safe_amount
            )
            self._attempt_by_endpoint[safe_endpoint] = (
                self._attempt_by_endpoint.get(safe_endpoint, 0) + safe_amount
            )
            self._attempt_by_action_scope[safe_action_scope] = (
                self._attempt_by_action_scope.get(safe_action_scope, 0) + safe_amount
            )

    def record_blocked(
        self,
        *,
        scope: str,
        action: str,
        endpoint: str,
        amount: int = 1,
    ) -> None:
        safe_amount = int(amount)
        if safe_amount <= 0:
            return

        safe_scope = _sanitize_key_part(scope)
        safe_action = _sanitize_key_part(action)
        safe_endpoint = _sanitize_key_part(endpoint)
        safe_action_scope = f"{safe_action}__{safe_scope}"

        with self._lock:
            self._blocked_total += safe_amount
            self._blocked_by_scope[safe_scope] = self._blocked_by_scope.get(safe_scope, 0) + safe_amount
            self._blocked_by_action[safe_action] = self._blocked_by_action.get(safe_action, 0) + safe_amount
            self._blocked_by_endpoint[safe_endpoint] = (
                self._blocked_by_endpoint.get(safe_endpoint, 0) + safe_amount
            )
            self._blocked_by_action_scope[safe_action_scope] = (
                self._blocked_by_action_scope.get(safe_action_scope, 0) + safe_amount
            )

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            scope_block_rate: dict[str, float] = {}
            for scope, attempts in self._attempt_by_scope.items():
                safe_attempts = max(0, int(attempts))
                if safe_attempts <= 0:
                    continue
                blocked = max(0, int(self._blocked_by_scope.get(scope, 0)))
                scope_block_rate[scope] = round(blocked / safe_attempts, 6)
            return {
                "attempt_total": int(self._attempt_total),
                "attempt_by_scope": dict(self._attempt_by_scope),
                "attempt_by_action": dict(self._attempt_by_action),
                "attempt_by_endpoint": dict(self._attempt_by_endpoint),
                "attempt_by_action_scope": dict(self._attempt_by_action_scope),
                "blocked_total": int(self._blocked_total),
                "blocked_by_scope": dict(self._blocked_by_scope),
                "blocked_by_action": dict(self._blocked_by_action),
                "blocked_by_endpoint": dict(self._blocked_by_endpoint),
                "blocked_by_action_scope": dict(self._blocked_by_action_scope),
                "block_rate_overall": round(self._blocked_total / self._attempt_total, 6)
                if self._attempt_total > 0
                else 0.0,
                "block_rate_by_scope": scope_block_rate,
            }


rate_limit_runtime_metrics = RateLimitRuntimeMetrics()
