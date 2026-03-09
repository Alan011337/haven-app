"""Cache eligibility and fingerprint match policy for AI router runtime."""

from __future__ import annotations

from typing import Protocol


RESULT_CACHE_STATUS_SUCCESS = "success"
RESULT_CACHE_STATUS_FAILURE = "failure"


class CacheRequestContext(Protocol):
    cache_allowed_max_safety_tier: int
    strict_schema_mode: bool
    input_fingerprint: str | None


class CacheFailure(Protocol):
    reason: str


def is_failure_cacheable(*, failure: CacheFailure) -> bool:
    return failure.reason not in {"timeout", "status_429", "status_5xx", "provider_exhausted"}


def contains_fallback_marker(parsed_payload: dict[str, object]) -> bool:
    marker = parsed_payload.get("fallback_marker")
    if isinstance(marker, bool):
        return marker
    if isinstance(marker, str):
        return marker.strip().lower() in {"1", "true", "yes", "fallback"}
    return False


def is_cache_eligible_success(
    *,
    request_context: CacheRequestContext,
    parsed_payload: dict[str, object],
) -> bool:
    safety_tier_raw = parsed_payload.get("safety_tier")
    if isinstance(safety_tier_raw, int) and safety_tier_raw > int(request_context.cache_allowed_max_safety_tier):
        return False
    if contains_fallback_marker(parsed_payload):
        return False
    if request_context.strict_schema_mode and not parsed_payload:
        return False
    return True


def matches_input_fingerprint(
    *,
    request_context: CacheRequestContext,
    cached_payload: dict[str, object],
) -> bool:
    expected = (request_context.input_fingerprint or "").strip()
    cached_raw = cached_payload.get("input_fingerprint")
    cached = str(cached_raw or "").strip()
    if not expected and not cached:
        return True
    if expected and cached and expected == cached:
        return True
    return False
