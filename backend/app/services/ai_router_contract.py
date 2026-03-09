"""Shared constants and datatypes for AI router runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

SUPPORTED_PROVIDERS = ("openai", "gemini")
DEFAULT_PROVIDER = "openai"
TASK_L1_CLASSIFY_EXTRACT = "l1_classify_extract"
TASK_L2_DEEP_REASONING = "l2_deep_reasoning"
SUPPORTED_ROUTER_TASKS = (TASK_L1_CLASSIFY_EXTRACT, TASK_L2_DEEP_REASONING)

REQUEST_CLASS_JOURNAL_ANALYSIS = "journal_analysis"
REQUEST_CLASS_COOLDOWN_REWRITE = "cooldown_rewrite"
SUPPORTED_REQUEST_CLASSES = (
    REQUEST_CLASS_JOURNAL_ANALYSIS,
    REQUEST_CLASS_COOLDOWN_REWRITE,
)

PROFILE_GEMINI_FREE = "gemini_free"
PROFILE_OPENAI_CHEAP = "openai_cheap"
PROFILE_OPENAI_PREMIUM = "openai_premium"
SUPPORTED_PROFILES = (
    PROFILE_GEMINI_FREE,
    PROFILE_OPENAI_CHEAP,
    PROFILE_OPENAI_PREMIUM,
)
PROFILE_PROVIDER_MAP = {
    PROFILE_GEMINI_FREE: "gemini",
    PROFILE_OPENAI_CHEAP: "openai",
    PROFILE_OPENAI_PREMIUM: "openai",
}

SUPPORTED_METRIC_FAILURE_REASONS = {
    "timeout",
    "status_429",
    "status_4xx",
    "status_5xx",
    "provider_adapter_missing",
    "provider_exhausted",
    "schema_validation_failed",
    "rate_limited_no_retry_after",
    "retry_after_exceeds_threshold",
    "retry_after_retry",
    "retry_backoff_retry",
    "cooldown_active",
    "max_elapsed_exceeded",
    "max_elapsed_exceeded_poll",
    "poll_exhausted_no_result",
    "fingerprint_mismatch",
    "redis_unavailable",
    "unexpected_error",
    "unknown",
}

SUPPORTED_DECISION_REASONS = {
    "configured_primary",
    "task_policy_l1",
    "task_policy_l2",
    "task_policy_unknown_normalized_to_l2",
    "primary_provider_normalized_to_default",
    "task_policy_l1_primary_normalized_to_default",
    "task_policy_l2_primary_normalized_to_default",
    "task_policy_unknown_normalized_to_l2_primary_normalized_to_default",
    "free_tier_first",
    "free_tier_first_quality_gate_red",
    "free_tier_first_cooldown_adjusted",
    "cache_hit",
    "cache_miss",
    "cache_miss_fingerprint_mismatch",
    "degraded_mode",
    "unknown",
}

SUPPORTED_IDEMPOTENCY_MISMATCH_ACTIONS = {
    "bypass_and_continue",
    "reject",
}

SUPPORTED_DUPLICATE_EXIT_ACTIONS = {
    "graceful_fallback",
    "failover_next",
}

SUPPORTED_JITTER_MODES = {
    "none",
    "full",
}

IDEMPOTENCY_STATUS_OK = "ok"
IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409 = "inflight_conflict_409"
IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422 = "fingerprint_mismatch_422"


@dataclass(frozen=True)
class AIRoute:
    selected_provider: str
    provider_chain: tuple[str, ...]
    fallback_enabled: bool
    reason: str


@dataclass(frozen=True)
class AIRouterRequestContext:
    request_class: str = REQUEST_CLASS_JOURNAL_ANALYSIS
    request_id: str | None = None
    idempotency_key: str | None = None
    input_fingerprint: str | None = None
    subject_key: str | None = None
    quality_gate_red: bool = False
    degraded_profiles: tuple[str, ...] = ()
    strict_schema_mode: bool = False
    prompt_version: str | None = None
    schema_version: str | None = None
    moderation_version: str | None = None
    relationship_mode: str | None = None
    cache_allowed_max_safety_tier: int = 1
    gate_decision_hash: str | None = None


@dataclass(frozen=True)
class AIProviderError(Exception):
    provider: str
    reason: str
    retryable: bool = True
    status_code: int | None = None
    retry_after_seconds: float | None = None

    def __str__(self) -> str:
        return f"{self.provider}:{self.reason}"


@dataclass(frozen=True)
class AIProviderAttemptFailure:
    provider: str
    reason: str
    retryable: bool


@dataclass(frozen=True)
class AIProviderRuntimeResult:
    provider: str
    model_version: str
    parsed: Any
    fallback_used: bool
    failures: tuple[AIProviderAttemptFailure, ...]
    cache_hit: bool = False
    idempotency_key: str | None = None
    decision_reason: str | None = None


@dataclass(frozen=True)
class AIProviderAdapter:
    provider: str
    run: Callable[[], Awaitable[tuple[Any, str]]]


class AIProviderFallbackExhaustedError(RuntimeError):
    def __init__(
        self,
        *,
        chain: tuple[str, ...],
        failures: tuple[AIProviderAttemptFailure, ...],
    ) -> None:
        super().__init__("ai provider fallback exhausted")
        self.chain = chain
        self.failures = failures


class AIProviderIdempotencyRejectedError(RuntimeError):
    def __init__(self, *, idempotency_key: str, reason: str) -> None:
        super().__init__("ai provider idempotency rejected")
        self.idempotency_key = idempotency_key
        self.reason = reason


@dataclass(frozen=True)
class AIRouterPolicy:
    free_tier_first_enabled: bool
    max_attempts_per_profile: int
    max_total_attempts: int
    max_elapsed_ms: int
    backoff_base_ms: int
    backoff_max_ms: int
    backoff_jitter_mode: str
    rate_limit_failover_threshold_seconds: float
    duplicate_poll_interval_ms: int
    duplicate_poll_jitter_ms_max: int
    duplicate_poll_max_consecutive_miss: int
    duplicate_fast_yield_remaining_budget_ms: int
    duplicate_exit_action: str
    schema_fail_cooldown_threshold: int
    schema_fail_window_seconds: int
    schema_fail_cooldown_seconds: int
    idempotency_mismatch_action: str
    result_cache_enabled: bool
    result_cache_mode: str
    result_cache_ttl_success_s_by_request_class: dict[str, int]
    result_cache_ttl_failure_s: int
    redis_key_prefix: str
    inflight_ttl_ms: int
    degraded_max_total_attempts: int
    degraded_disable_sleep: bool
    degraded_disable_cache: bool
    degraded_disable_poll: bool
    profile_candidates_by_request_class: dict[str, tuple[str, ...]]
