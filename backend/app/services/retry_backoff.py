from __future__ import annotations

import random


def compute_exponential_backoff_seconds(
    *,
    attempt: int,
    base_seconds: float,
    max_seconds: float,
    jitter_ratio: float = 0.0,
) -> float:
    """
    Compute bounded exponential backoff with optional positive jitter.

    attempt: 0-based retry attempt.
    jitter_ratio: 0.0 means deterministic backoff.
    """
    safe_attempt = max(0, int(attempt))
    safe_base = max(0.001, float(base_seconds))
    safe_max = max(safe_base, float(max_seconds))
    safe_jitter = min(1.0, max(0.0, float(jitter_ratio)))

    delay = min(safe_base * (2**safe_attempt), safe_max)
    if safe_jitter <= 0:
        return delay

    jitter = delay * safe_jitter * random.random()
    return min(safe_max, delay + jitter)
