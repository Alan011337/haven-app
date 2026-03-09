"""Reusable retry/backoff helpers for AI router runtime."""

from __future__ import annotations

import random
from typing import Protocol


class RetryBackoffPolicyLike(Protocol):
    backoff_base_ms: int
    backoff_max_ms: int
    backoff_jitter_mode: str


def parse_retry_after_seconds(retry_after: float | int | None) -> float | None:
    if retry_after is None:
        return None
    safe_value = float(retry_after)
    if safe_value < 0:
        return 0.0
    return safe_value


def compute_backoff_seconds(*, attempt: int, policy: RetryBackoffPolicyLike) -> float:
    if policy.backoff_base_ms <= 0 or policy.backoff_max_ms <= 0:
        return 0.0

    growth_ms = min(
        float(policy.backoff_max_ms),
        float(policy.backoff_base_ms) * (2 ** max(0, attempt - 1)),
    )
    if growth_ms <= 0:
        return 0.0

    if policy.backoff_jitter_mode == "full":
        return random.uniform(0.0, growth_ms / 1000.0)
    return growth_ms / 1000.0
