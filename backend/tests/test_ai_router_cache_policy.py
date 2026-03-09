from dataclasses import dataclass

from app.services.ai_router_cache_policy import (
    contains_fallback_marker,
    is_cache_eligible_success,
    is_failure_cacheable,
    matches_input_fingerprint,
)


@dataclass(frozen=True)
class _Ctx:
    cache_allowed_max_safety_tier: int = 1
    strict_schema_mode: bool = False
    input_fingerprint: str | None = None


@dataclass(frozen=True)
class _Failure:
    reason: str


def test_cache_eligible_success_rejects_high_safety_tier() -> None:
    assert not is_cache_eligible_success(
        request_context=_Ctx(cache_allowed_max_safety_tier=1),
        parsed_payload={"safety_tier": 3},
    )


def test_cache_eligible_success_rejects_fallback_marker() -> None:
    assert not is_cache_eligible_success(
        request_context=_Ctx(),
        parsed_payload={"fallback_marker": True},
    )


def test_cache_eligible_success_accepts_normal_payload() -> None:
    assert is_cache_eligible_success(
        request_context=_Ctx(),
        parsed_payload={"safety_tier": 1, "summary": "ok"},
    )


def test_contains_fallback_marker_supports_string_marker() -> None:
    assert contains_fallback_marker({"fallback_marker": "true"})


def test_failure_cacheability_rejects_transient_failures() -> None:
    assert not is_failure_cacheable(failure=_Failure(reason="timeout"))
    assert not is_failure_cacheable(failure=_Failure(reason="status_429"))
    assert is_failure_cacheable(failure=_Failure(reason="schema_validation_failed"))


def test_matches_input_fingerprint_requires_exact_match() -> None:
    assert matches_input_fingerprint(
        request_context=_Ctx(input_fingerprint="abc"),
        cached_payload={"input_fingerprint": "abc"},
    )
    assert not matches_input_fingerprint(
        request_context=_Ctx(input_fingerprint="abc"),
        cached_payload={"input_fingerprint": "xyz"},
    )
