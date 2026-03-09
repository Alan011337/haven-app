"""AI router support helpers extracted from the main runtime module."""

from __future__ import annotations

from collections import deque
import time
from threading import Lock
from typing import Any, Callable, Protocol

from app.core.config import settings
from app.services.ai_router_cache_policy import (
    RESULT_CACHE_STATUS_FAILURE as _RESULT_CACHE_STATUS_FAILURE,
)
from app.services.ai_router_contract import (
    AIProviderRuntimeResult,
    AIRoute,
    AIRouterPolicy,
    AIRouterRequestContext,
    PROFILE_GEMINI_FREE,
    PROFILE_OPENAI_PREMIUM,
    PROFILE_PROVIDER_MAP,
    REQUEST_CLASS_JOURNAL_ANALYSIS,
    SUPPORTED_DECISION_REASONS,
    SUPPORTED_METRIC_FAILURE_REASONS,
    SUPPORTED_PROFILES,
    SUPPORTED_PROVIDERS,
    SUPPORTED_REQUEST_CLASSES,
)
from app.services.ai_router_metrics import sanitize_metric_key as _sanitize_metric_key
from app.services.ai_router_metrics import sanitize_metric_label as _sanitize_metric_label


class AIRouterSharedStateStoreLike(Protocol):
    @property
    def degraded_mode(self) -> bool:
        ...

    def get_json(self, key: str) -> dict[str, Any] | None:
        ...

    def set_json(self, key: str, value: dict[str, Any], *, ttl_seconds: int) -> None:
        ...

    def incr_with_ttl(self, key: str, *, ttl_seconds: int) -> int:
        ...


class AIRouterRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._counters: dict[str, int] = {}
        self._attempt_events: deque[tuple[float, bool]] = deque()
        self._state: dict[str, Any] = {
            "shared_state_backend": "memory",
            "redis_degraded_mode": False,
        }

    def increment(self, key: str, *, amount: int = 1) -> None:
        if amount <= 0:
            return
        safe_key = _sanitize_metric_key(key)
        with self._lock:
            self._counters[safe_key] = self._counters.get(safe_key, 0) + amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    @staticmethod
    def _burn_rate_config() -> dict[str, float | int]:
        error_budget = max(
            0.0001,
            min(
                1.0,
                float(
                    getattr(
                        settings,
                        "AI_ROUTER_BURN_RATE_ERROR_BUDGET_FRACTION",
                        0.01,
                    )
                ),
            ),
        )
        fast_window = max(
            30,
            int(getattr(settings, "AI_ROUTER_BURN_RATE_FAST_WINDOW_SECONDS", 300)),
        )
        slow_window = max(
            fast_window,
            int(getattr(settings, "AI_ROUTER_BURN_RATE_SLOW_WINDOW_SECONDS", 3600)),
        )
        fast_threshold = max(
            0.1,
            float(getattr(settings, "AI_ROUTER_BURN_RATE_FAST_THRESHOLD", 14.4)),
        )
        slow_threshold = max(
            0.1,
            float(getattr(settings, "AI_ROUTER_BURN_RATE_SLOW_THRESHOLD", 6.0)),
        )
        min_attempts_fast = max(
            1,
            int(getattr(settings, "AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_FAST", 20)),
        )
        min_attempts_slow = max(
            min_attempts_fast,
            int(getattr(settings, "AI_ROUTER_BURN_RATE_MIN_ATTEMPTS_SLOW", 100)),
        )
        return {
            "error_budget_fraction": error_budget,
            "fast_window_seconds": fast_window,
            "slow_window_seconds": slow_window,
            "fast_threshold": fast_threshold,
            "slow_threshold": slow_threshold,
            "min_attempts_fast": min_attempts_fast,
            "min_attempts_slow": min_attempts_slow,
        }

    def _purge_attempt_events_locked(self, *, now_ts: float) -> None:
        config = self._burn_rate_config()
        max_window = int(config["slow_window_seconds"])
        cutoff = now_ts - float(max_window)
        while self._attempt_events and self._attempt_events[0][0] < cutoff:
            self._attempt_events.popleft()

    def record_attempt(self, *, success: bool, now_ts: float | None = None) -> None:
        timestamp = float(now_ts if now_ts is not None else time.time())
        with self._lock:
            self._attempt_events.append((timestamp, not success))
            self._purge_attempt_events_locked(now_ts=timestamp)
            counter_key = (
                "ai_router_burn_rate_sample_success_total"
                if success
                else "ai_router_burn_rate_sample_failure_total"
            )
            self._counters[counter_key] = self._counters.get(counter_key, 0) + 1

    @staticmethod
    def _window_payload(
        *,
        attempts_total: int,
        failures_total: int,
        min_attempts: int,
        threshold: float,
        window_seconds: int,
        error_budget_fraction: float,
    ) -> dict[str, Any]:
        failure_rate = (
            0.0 if attempts_total <= 0 else float(failures_total) / float(attempts_total)
        )
        burn_rate = (
            0.0
            if attempts_total <= 0
            else failure_rate / max(error_budget_fraction, 0.0001)
        )
        return {
            "window_seconds": int(window_seconds),
            "attempts_total": int(attempts_total),
            "failures_total": int(failures_total),
            "failure_rate": round(failure_rate, 6),
            "burn_rate": round(burn_rate, 6),
            "threshold": float(threshold),
            "min_attempts": int(min_attempts),
            "enough_samples": attempts_total >= min_attempts,
        }

    def burn_rate_snapshot(self, *, now_ts: float | None = None) -> dict[str, Any]:
        timestamp = float(now_ts if now_ts is not None else time.time())
        config = self._burn_rate_config()
        with self._lock:
            self._purge_attempt_events_locked(now_ts=timestamp)
            events = tuple(self._attempt_events)

        def _count_window(window_seconds: int) -> tuple[int, int]:
            cutoff = timestamp - float(window_seconds)
            attempts = 0
            failures = 0
            for event_ts, is_failure in events:
                if event_ts < cutoff:
                    continue
                attempts += 1
                if is_failure:
                    failures += 1
            return attempts, failures

        fast_attempts, fast_failures = _count_window(int(config["fast_window_seconds"]))
        slow_attempts, slow_failures = _count_window(int(config["slow_window_seconds"]))

        fast_window = self._window_payload(
            attempts_total=fast_attempts,
            failures_total=fast_failures,
            min_attempts=int(config["min_attempts_fast"]),
            threshold=float(config["fast_threshold"]),
            window_seconds=int(config["fast_window_seconds"]),
            error_budget_fraction=float(config["error_budget_fraction"]),
        )
        slow_window = self._window_payload(
            attempts_total=slow_attempts,
            failures_total=slow_failures,
            min_attempts=int(config["min_attempts_slow"]),
            threshold=float(config["slow_threshold"]),
            window_seconds=int(config["slow_window_seconds"]),
            error_budget_fraction=float(config["error_budget_fraction"]),
        )

        reasons: list[str] = []
        status = "ok"
        if not fast_window["enough_samples"] and not slow_window["enough_samples"]:
            status = "insufficient_data"
            reasons.append("ai_router_burn_rate_insufficient_samples")
        else:
            fast_degraded = bool(
                fast_window["enough_samples"]
                and fast_window["burn_rate"] > fast_window["threshold"]
            )
            slow_degraded = bool(
                slow_window["enough_samples"]
                and slow_window["burn_rate"] > slow_window["threshold"]
            )
            if fast_degraded and slow_degraded:
                status = "degraded"
                reasons.append("ai_router_burn_rate_fast_and_slow_exceeded")
            elif fast_degraded:
                status = "degraded"
                reasons.append("ai_router_burn_rate_fast_exceeded")
            elif slow_degraded:
                status = "degraded"
                reasons.append("ai_router_burn_rate_slow_exceeded")

        return {
            "status": status,
            "reasons": reasons,
            "error_budget_fraction": float(config["error_budget_fraction"]),
            "fast_window": fast_window,
            "slow_window": slow_window,
        }

    def state_snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._state)

    def set_state(self, key: str, value: Any) -> None:
        with self._lock:
            self._state[key] = value

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._attempt_events.clear()
            self._state = {
                "shared_state_backend": "memory",
                "redis_degraded_mode": False,
            }


def provider_metric_bucket(provider: str) -> str:
    return _sanitize_metric_label(
        raw=provider,
        allowlist=set(SUPPORTED_PROVIDERS) | {"unknown"},
    )


def profile_metric_bucket(profile: str) -> str:
    return _sanitize_metric_label(
        raw=profile,
        allowlist=set(SUPPORTED_PROFILES) | {"unknown"},
    )


def reason_metric_bucket(reason: str | None) -> str:
    return _sanitize_metric_label(
        raw=(reason or "unknown"),
        allowlist=set(SUPPORTED_METRIC_FAILURE_REASONS),
    )


def decision_reason_bucket(reason: str | None) -> str:
    return _sanitize_metric_label(
        raw=(reason or "unknown"),
        allowlist=set(SUPPORTED_DECISION_REASONS),
    )


def metric_key(kind: str, provider: str, reason: str | None = None, *, profile: str | None = None) -> str:
    provider_key = provider_metric_bucket(provider)
    profile_key = profile_metric_bucket(profile or "unknown")
    if not reason:
        return f"ai_router_{kind}_{provider_key}_{profile_key}_total"
    reason_key = reason_metric_bucket(reason)
    return f"ai_router_{kind}_{provider_key}_{profile_key}_{reason_key}_total"


def decision_metric_key(*, request_class: str, profile: str, reason: str) -> str:
    class_key = _sanitize_metric_label(
        raw=request_class,
        allowlist=set(SUPPORTED_REQUEST_CLASSES) | {"unknown"},
    )
    profile_key = profile_metric_bucket(profile)
    reason_key = decision_reason_bucket(reason)
    return f"ai_router_decision_{class_key}_{profile_key}_{reason_key}_total"


def resolve_profile_chain(
    *,
    route: AIRoute,
    request_context: AIRouterRequestContext,
    policy: AIRouterPolicy,
    store: AIRouterSharedStateStoreLike,
    normalize_request_class: Callable[[str | None], str],
    normalize_provider: Callable[[str | None], str],
    is_profile_on_cooldown: Callable[..., bool],
    metric_increment: Callable[[str], None],
    metric_key_builder: Callable[..., str],
) -> tuple[tuple[str, ...], str]:
    request_class = normalize_request_class(request_context.request_class)

    if not policy.free_tier_first_enabled:
        fallback_profiles = tuple(
            PROFILE_GEMINI_FREE
            if normalize_provider(provider) == "gemini"
            else PROFILE_OPENAI_PREMIUM
            for provider in route.provider_chain
        )
        return fallback_profiles or (PROFILE_OPENAI_PREMIUM,), route.reason

    candidates = list(policy.profile_candidates_by_request_class.get(request_class, ()))
    if not candidates:
        candidates = [
            PROFILE_GEMINI_FREE
            if normalize_provider(provider) == "gemini"
            else PROFILE_OPENAI_PREMIUM
            for provider in route.provider_chain
        ]
    decision_reason = "free_tier_first"

    degraded_profiles = set(
        profile.strip().lower() for profile in request_context.degraded_profiles
    )
    if request_context.quality_gate_red:
        decision_reason = "free_tier_first_quality_gate_red"
        prioritized: list[str] = []
        deferred: list[str] = []
        for profile in candidates:
            if profile == PROFILE_GEMINI_FREE:
                deferred.append(profile)
            else:
                prioritized.append(profile)
        candidates = prioritized + deferred

    filtered: list[str] = []
    cooldown_filtered = False
    for profile in candidates:
        normalized_profile = profile_metric_bucket(profile)
        if normalized_profile == "unknown":
            continue
        if profile in degraded_profiles:
            cooldown_filtered = True
            metric_increment(
                metric_key_builder(
                    "skip",
                    PROFILE_PROVIDER_MAP.get(profile, "unknown"),
                    "quality_gate_degraded_profile",
                    profile=profile,
                )
            )
            continue
        if is_profile_on_cooldown(
            store=store,
            request_class=request_class,
            profile=profile,
        ):
            cooldown_filtered = True
            metric_increment(
                metric_key_builder(
                    "skip",
                    PROFILE_PROVIDER_MAP.get(profile, "unknown"),
                    "cooldown_active",
                    profile=profile,
                )
            )
            continue
        filtered.append(profile)

    if cooldown_filtered and decision_reason == "free_tier_first":
        decision_reason = "free_tier_first_cooldown_adjusted"

    if not filtered:
        fallback_profiles = tuple(
            PROFILE_GEMINI_FREE
            if normalize_provider(provider) == "gemini"
            else PROFILE_OPENAI_PREMIUM
            for provider in route.provider_chain
        )
        return fallback_profiles or (PROFILE_OPENAI_PREMIUM,), decision_reason

    return tuple(filtered), decision_reason


def serialize_parsed(parsed: Any) -> dict[str, Any]:
    if hasattr(parsed, "model_dump"):
        dumped = parsed.model_dump()
        if isinstance(dumped, dict):
            return dumped
    if isinstance(parsed, dict):
        return dict(parsed)
    raise TypeError("parsed payload is not serializable")


def result_from_cache_payload(
    *,
    cached_payload: dict[str, Any],
    idempotency_key: str,
) -> AIProviderRuntimeResult | None:
    parsed_payload = cached_payload.get("parsed_payload")
    if not isinstance(parsed_payload, dict):
        return None
    provider = provider_metric_bucket(str(cached_payload.get("provider") or "unknown"))
    return AIProviderRuntimeResult(
        provider=provider,
        model_version=str(cached_payload.get("model_version") or ""),
        parsed=parsed_payload,
        fallback_used=False,
        failures=(),
        cache_hit=True,
        idempotency_key=idempotency_key,
        decision_reason="cache_hit",
    )


def build_cache_payload(
    *,
    request_context: AIRouterRequestContext,
    provider: str,
    model_version: str,
    parsed_payload: dict[str, Any],
    status: str,
    gate_decision_hash: str | None,
    current_unix_ms: Callable[[], int],
    normalize_request_class: Callable[[str | None], str],
) -> dict[str, Any]:
    return {
        "status": status,
        "provider": provider_metric_bucket(provider),
        "model_version": str(model_version or ""),
        "parsed_payload": parsed_payload,
        "input_fingerprint": (request_context.input_fingerprint or "").strip() or None,
        "request_class": normalize_request_class(request_context.request_class),
        "created_at_unix_ms": current_unix_ms(),
        "routing_policy_version": "router_policy_v1",
        "router_policy_schema_version": "1.0.0",
        "gate_decision_hash": gate_decision_hash or request_context.gate_decision_hash,
        "moderation_version": request_context.moderation_version,
        "prompt_version": request_context.prompt_version,
        "schema_version": request_context.schema_version,
        "relationship_mode": request_context.relationship_mode,
    }


def get_cooldown_until_ms(
    *,
    store: AIRouterSharedStateStoreLike,
    request_class: str,
    profile: str,
    schema_cooldown_key_builder: Callable[..., str],
) -> int:
    key = schema_cooldown_key_builder(request_class=request_class, profile=profile)
    raw = store.get_json(key)
    if not isinstance(raw, dict):
        return 0
    value = raw.get("until_ms")
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def is_profile_on_cooldown(
    *,
    store: AIRouterSharedStateStoreLike,
    request_class: str,
    profile: str,
    current_unix_ms: Callable[[], int],
    get_cooldown_until_ms: Callable[..., int],
) -> bool:
    until_ms = get_cooldown_until_ms(
        store=store,
        request_class=request_class,
        profile=profile,
    )
    if until_ms <= 0:
        return False
    return current_unix_ms() < int(until_ms)


def mark_profile_cooldown(
    *,
    store: AIRouterSharedStateStoreLike,
    request_class: str,
    profile: str,
    cooldown_seconds: int,
    current_unix_ms: Callable[[], int],
    schema_cooldown_key_builder: Callable[..., str],
) -> None:
    until_ms = current_unix_ms() + max(1, int(cooldown_seconds)) * 1000
    key = schema_cooldown_key_builder(request_class=request_class, profile=profile)
    store.set_json(
        key,
        {"until_ms": until_ms},
        ttl_seconds=max(1, int(cooldown_seconds)),
    )


def record_schema_failure(
    *,
    store: AIRouterSharedStateStoreLike,
    request_class: str,
    profile: str,
    policy: AIRouterPolicy,
    schema_fail_counter_key_builder: Callable[..., str],
    mark_profile_cooldown: Callable[..., None],
    metric_increment: Callable[[str], None],
) -> bool:
    if store.degraded_mode and policy.degraded_disable_cache:
        metric_increment("ai_router_schema_cooldown_disabled_redis_down_total")
        return False

    key = schema_fail_counter_key_builder(request_class=request_class, profile=profile)
    count = store.incr_with_ttl(
        key,
        ttl_seconds=max(1, policy.schema_fail_window_seconds),
    )
    if count >= policy.schema_fail_cooldown_threshold:
        mark_profile_cooldown(
            store=store,
            request_class=request_class,
            profile=profile,
            cooldown_seconds=policy.schema_fail_cooldown_seconds,
        )
        metric_increment("ai_router_schema_cooldown_activated_total")
        return True
    return False


def get_result_cache_ttl(
    *,
    policy: AIRouterPolicy,
    request_class: str,
    status: str,
) -> int:
    if status == _RESULT_CACHE_STATUS_FAILURE:
        return max(1, int(policy.result_cache_ttl_failure_s))
    return max(
        1,
        int(
            policy.result_cache_ttl_success_s_by_request_class.get(
                request_class,
                policy.result_cache_ttl_success_s_by_request_class.get(
                    REQUEST_CLASS_JOURNAL_ANALYSIS,
                    120,
                ),
            )
        ),
    )


def sleep_disabled(*, policy: AIRouterPolicy, store: AIRouterSharedStateStoreLike) -> bool:
    return bool(store.degraded_mode and policy.degraded_disable_sleep)
