"""Shared runtime helper utilities for ai_router."""

from __future__ import annotations

import time
from typing import Callable, Protocol

from app.services.ai_router_identity import build_router_key as _build_router_key_from_identity


class _RequestContextLike(Protocol):
    request_class: str
    subject_key: str | None


def elapsed_ms(*, start_monotonic: float, now_func: Callable[[], float]) -> int:
    return max(0, int((now_func() - start_monotonic) * 1000.0))


def remaining_ms(
    *,
    start_monotonic: float,
    now_func: Callable[[], float],
    max_elapsed_ms: int,
) -> int:
    return max(
        0,
        int(max_elapsed_ms - elapsed_ms(start_monotonic=start_monotonic, now_func=now_func)),
    )


def make_router_key(
    *,
    request_context: _RequestContextLike,
    idempotency_key: str,
    normalize_request_class: Callable[[str | None], str],
) -> str:
    subject_key = (request_context.subject_key or "anonymous").strip() or "anonymous"
    request_class = normalize_request_class(request_context.request_class)
    return _build_router_key_from_identity(
        subject_key=subject_key,
        request_class=request_class,
        idempotency_key=idempotency_key,
    )


def result_cache_key(router_key: str) -> str:
    return f"result:{router_key}"


def inflight_key(router_key: str) -> str:
    return f"inflight:{router_key}"


def schema_fail_counter_key(*, request_class: str, profile: str) -> str:
    return f"schema_fail_count:{request_class}:{profile}"


def schema_cooldown_key(*, request_class: str, profile: str) -> str:
    return f"schema_cooldown_until_ms:{request_class}:{profile}"


def current_unix_ms() -> int:
    return int(time.time() * 1000)
