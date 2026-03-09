"""AI provider routing + runtime fallback helpers (P1-I)."""

from __future__ import annotations

import asyncio
import json
import random
import time
import uuid
from threading import Lock
from typing import Any, Awaitable, Callable, Protocol

from app.core.config import settings
from app.services.ai_router_contract import (
    AIProviderAdapter,
    AIProviderAttemptFailure,
    AIProviderError,
    AIProviderFallbackExhaustedError,
    AIProviderIdempotencyRejectedError,
    AIProviderRuntimeResult,
    AIRoute,
    AIRouterPolicy,
    AIRouterRequestContext,
    DEFAULT_PROVIDER,
    IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422,
    IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409,
    IDEMPOTENCY_STATUS_OK,
    PROFILE_GEMINI_FREE,
    PROFILE_OPENAI_CHEAP,
    PROFILE_OPENAI_PREMIUM,
    PROFILE_PROVIDER_MAP,
    REQUEST_CLASS_COOLDOWN_REWRITE,
    REQUEST_CLASS_JOURNAL_ANALYSIS,
    SUPPORTED_DUPLICATE_EXIT_ACTIONS,
    SUPPORTED_IDEMPOTENCY_MISMATCH_ACTIONS,
    SUPPORTED_JITTER_MODES,
    SUPPORTED_PROFILES as _SUPPORTED_PROFILES,
    SUPPORTED_PROVIDERS,
    SUPPORTED_REQUEST_CLASSES,
    SUPPORTED_ROUTER_TASKS,
    TASK_L1_CLASSIFY_EXTRACT,
    TASK_L2_DEEP_REASONING,
)
from app.services.ai_router_cache_policy import (
    RESULT_CACHE_STATUS_FAILURE as _RESULT_CACHE_STATUS_FAILURE,
    RESULT_CACHE_STATUS_SUCCESS as _RESULT_CACHE_STATUS_SUCCESS,
    is_cache_eligible_success as _is_cache_eligible_success,
    is_failure_cacheable as _is_failure_cacheable,
    matches_input_fingerprint as _matches_input_fingerprint,
)
from app.services.ai_router_identity import (
    build_input_fingerprint as _build_input_fingerprint,
    build_normalized_content_hash as _build_normalized_content_hash,
    canonical_json_dumps as _canonical_json_dumps_from_identity,
    normalize_idempotency_key as _normalize_idempotency_key,
)
from app.services.ai_router_retry import (
    compute_backoff_seconds as _compute_backoff_seconds_from_module,
    parse_retry_after_seconds as _parse_retry_after_seconds_from_module,
)
from app.services.ai_router_support import (
    AIRouterRuntimeMetrics,
    build_cache_payload as _build_cache_payload_from_support,
    decision_metric_key as _decision_metric_key_from_support,
    decision_reason_bucket as _decision_reason_bucket_from_support,
    get_cooldown_until_ms as _get_cooldown_until_ms_from_support,
    get_result_cache_ttl as _get_result_cache_ttl_from_support,
    is_profile_on_cooldown as _is_profile_on_cooldown_from_support,
    mark_profile_cooldown as _mark_profile_cooldown_from_support,
    metric_key as _metric_key_from_support,
    profile_metric_bucket as _profile_metric_bucket_from_support,
    provider_metric_bucket as _provider_metric_bucket_from_support,
    reason_metric_bucket as _reason_metric_bucket_from_support,
    record_schema_failure as _record_schema_failure_from_support,
    resolve_profile_chain as _resolve_profile_chain_from_support,
    result_from_cache_payload as _result_from_cache_payload_from_support,
    serialize_parsed as _serialize_parsed_from_support,
    sleep_disabled as _sleep_disabled_from_support,
)
from app.services.ai_router_runtime_helpers import (
    current_unix_ms as _current_unix_ms_from_helpers,
    elapsed_ms as _elapsed_ms_from_helpers,
    inflight_key as _inflight_key_from_helpers,
    make_router_key as _make_router_key_from_helpers,
    remaining_ms as _remaining_ms_from_helpers,
    result_cache_key as _result_cache_key_from_helpers,
    schema_cooldown_key as _schema_cooldown_key_from_helpers,
    schema_fail_counter_key as _schema_fail_counter_key_from_helpers,
)
_INFLIGHT_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""

ai_router_runtime_metrics = AIRouterRuntimeMetrics()
SUPPORTED_PROFILES = _SUPPORTED_PROFILES


def build_ai_router_runtime_payload() -> dict[str, Any]:
    return {
        "counters": ai_router_runtime_metrics.snapshot(),
        "state": ai_router_runtime_metrics.state_snapshot(),
        "burn_rate": ai_router_runtime_metrics.burn_rate_snapshot(),
    }


def _provider_metric_bucket(provider: str) -> str:
    return _provider_metric_bucket_from_support(provider)


def _profile_metric_bucket(profile: str) -> str:
    return _profile_metric_bucket_from_support(profile)


def _reason_metric_bucket(reason: str | None) -> str:
    return _reason_metric_bucket_from_support(reason)


def _decision_reason_bucket(reason: str | None) -> str:
    return _decision_reason_bucket_from_support(reason)


class AIRouterSharedStateStore(Protocol):
    @property
    def backend_name(self) -> str:
        ...

    @property
    def degraded_mode(self) -> bool:
        ...

    def get_json(self, key: str) -> dict[str, Any] | None:
        ...

    def set_json(self, key: str, value: dict[str, Any], *, ttl_seconds: int) -> None:
        ...

    def reserve_inflight(self, key: str, *, token: str, ttl_ms: int) -> bool:
        ...

    def release_inflight(self, key: str, *, token: str) -> None:
        ...

    def incr_with_ttl(self, key: str, *, ttl_seconds: int) -> int:
        ...

    def get_int(self, key: str) -> int:
        ...


class InMemoryAIRouterSharedStateStore:
    def __init__(self, *, degraded_mode: bool = False) -> None:
        self._lock = Lock()
        self._json_data: dict[str, tuple[dict[str, Any], float]] = {}
        self._raw_data: dict[str, tuple[str, float]] = {}
        self._int_data: dict[str, tuple[int, float]] = {}
        self._degraded_mode = degraded_mode

    @property
    def backend_name(self) -> str:
        return "memory"

    @property
    def degraded_mode(self) -> bool:
        return self._degraded_mode

    def _now(self) -> float:
        return time.time()

    def _purge_expired(self) -> None:
        now = self._now()
        for store in (self._json_data, self._raw_data, self._int_data):
            expired = [key for key, (_, exp) in store.items() if exp <= now]
            for key in expired:
                store.pop(key, None)

    def get_json(self, key: str) -> dict[str, Any] | None:
        with self._lock:
            self._purge_expired()
            payload = self._json_data.get(key)
            if payload is None:
                return None
            return dict(payload[0])

    def set_json(self, key: str, value: dict[str, Any], *, ttl_seconds: int) -> None:
        safe_ttl = max(1, int(ttl_seconds))
        with self._lock:
            self._json_data[key] = (dict(value), self._now() + float(safe_ttl))

    def reserve_inflight(self, key: str, *, token: str, ttl_ms: int) -> bool:
        safe_ttl = max(50, int(ttl_ms))
        with self._lock:
            self._purge_expired()
            if key in self._raw_data:
                return False
            self._raw_data[key] = (token, self._now() + float(safe_ttl) / 1000.0)
            return True

    def release_inflight(self, key: str, *, token: str) -> None:
        with self._lock:
            self._purge_expired()
            current = self._raw_data.get(key)
            if current is None:
                return
            if current[0] != token:
                return
            self._raw_data.pop(key, None)

    def incr_with_ttl(self, key: str, *, ttl_seconds: int) -> int:
        safe_ttl = max(1, int(ttl_seconds))
        with self._lock:
            self._purge_expired()
            current = self._int_data.get(key)
            current_value = 0 if current is None else int(current[0])
            next_value = current_value + 1
            self._int_data[key] = (next_value, self._now() + float(safe_ttl))
            return next_value

    def get_int(self, key: str) -> int:
        with self._lock:
            self._purge_expired()
            payload = self._int_data.get(key)
            return 0 if payload is None else int(payload[0])


class RedisAIRouterSharedStateStore:
    def __init__(self, *, redis_url: str, key_prefix: str) -> None:
        try:
            import redis
        except Exception as exc:  # pragma: no cover - runtime dependency
            raise RuntimeError("redis package unavailable") from exc

        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_prefix = key_prefix
        try:
            self._client.ping()
        except Exception as exc:
            raise RuntimeError("redis ping failed") from exc

    @property
    def backend_name(self) -> str:
        return "redis"

    @property
    def degraded_mode(self) -> bool:
        return False

    def _full_key(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    def get_json(self, key: str) -> dict[str, Any] | None:
        raw = self._client.get(self._full_key(key))
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            self._client.delete(self._full_key(key))
            return None
        if not isinstance(payload, dict):
            self._client.delete(self._full_key(key))
            return None
        return payload

    def set_json(self, key: str, value: dict[str, Any], *, ttl_seconds: int) -> None:
        safe_ttl = max(1, int(ttl_seconds))
        payload = json.dumps(value, separators=(",", ":"), ensure_ascii=True)
        self._client.set(self._full_key(key), payload, ex=safe_ttl)

    def reserve_inflight(self, key: str, *, token: str, ttl_ms: int) -> bool:
        safe_ttl_ms = max(50, int(ttl_ms))
        acquired = self._client.set(
            self._full_key(key),
            token,
            nx=True,
            px=safe_ttl_ms,
        )
        return bool(acquired)

    def release_inflight(self, key: str, *, token: str) -> None:
        try:
            self._client.eval(
                _INFLIGHT_RELEASE_LUA,
                1,
                self._full_key(key),
                token,
            )
        except Exception:
            # lock release is best effort; never break caller flow
            pass

    def incr_with_ttl(self, key: str, *, ttl_seconds: int) -> int:
        safe_ttl = max(1, int(ttl_seconds))
        full_key = self._full_key(key)
        pipe = self._client.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, safe_ttl)
        value, _ = pipe.execute()
        return int(value or 0)

    def get_int(self, key: str) -> int:
        raw = self._client.get(self._full_key(key))
        if raw is None:
            return 0
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0


_shared_state_lock = Lock()
_shared_state_store: AIRouterSharedStateStore | None = None


def _load_policy() -> AIRouterPolicy:
    default_candidates = {
        REQUEST_CLASS_JOURNAL_ANALYSIS: (
            PROFILE_GEMINI_FREE,
            PROFILE_OPENAI_CHEAP,
            PROFILE_OPENAI_PREMIUM,
        ),
        REQUEST_CLASS_COOLDOWN_REWRITE: (
            PROFILE_GEMINI_FREE,
            PROFILE_OPENAI_CHEAP,
        ),
    }

    return AIRouterPolicy(
        free_tier_first_enabled=bool(
            getattr(settings, "AI_ROUTER_FREE_TIER_FIRST_ENABLED", True)
        ),
        max_attempts_per_profile=max(
            1,
            int(getattr(settings, "AI_ROUTER_MAX_ATTEMPTS_PER_PROFILE", 2)),
        ),
        max_total_attempts=max(1, int(getattr(settings, "AI_ROUTER_MAX_TOTAL_ATTEMPTS", 4))),
        max_elapsed_ms=max(200, int(getattr(settings, "AI_ROUTER_MAX_ELAPSED_MS", 6500))),
        backoff_base_ms=max(0, int(getattr(settings, "AI_ROUTER_BACKOFF_BASE_MS", 400))),
        backoff_max_ms=max(0, int(getattr(settings, "AI_ROUTER_BACKOFF_MAX_MS", 8000))),
        backoff_jitter_mode=(
            str(getattr(settings, "AI_ROUTER_BACKOFF_JITTER_MODE", "full"))
            .strip()
            .lower()
        ),
        rate_limit_failover_threshold_seconds=max(
            0.0,
            float(
                getattr(settings, "AI_ROUTER_RATE_LIMIT_FAILOVER_THRESHOLD_SECONDS", 2.0)
            ),
        ),
        duplicate_poll_interval_ms=max(
            10,
            int(getattr(settings, "AI_ROUTER_DUPLICATE_POLL_INTERVAL_MS", 80)),
        ),
        duplicate_poll_jitter_ms_max=max(
            0,
            int(getattr(settings, "AI_ROUTER_DUPLICATE_POLL_JITTER_MS_MAX", 20)),
        ),
        duplicate_poll_max_consecutive_miss=max(
            1,
            int(getattr(settings, "AI_ROUTER_DUPLICATE_POLL_MAX_CONSECUTIVE_MISS", 3)),
        ),
        duplicate_fast_yield_remaining_budget_ms=max(
            0,
            int(
                getattr(
                    settings,
                    "AI_ROUTER_DUPLICATE_FAST_YIELD_REMAINING_BUDGET_MS",
                    200,
                )
            ),
        ),
        duplicate_exit_action=str(
            getattr(
                settings,
                "AI_ROUTER_DUPLICATE_EXIT_ACTION",
                "graceful_fallback",
            )
        )
        .strip()
        .lower(),
        schema_fail_cooldown_threshold=max(
            1,
            int(getattr(settings, "AI_ROUTER_SCHEMA_FAIL_COOLDOWN_THRESHOLD", 3)),
        ),
        schema_fail_window_seconds=max(
            1,
            int(getattr(settings, "AI_ROUTER_SCHEMA_FAIL_WINDOW_SECONDS", 60)),
        ),
        schema_fail_cooldown_seconds=max(
            1,
            int(getattr(settings, "AI_ROUTER_SCHEMA_FAIL_COOLDOWN_SECONDS", 120)),
        ),
        idempotency_mismatch_action=str(
            getattr(
                settings,
                "AI_ROUTER_IDEMPOTENCY_MISMATCH_ACTION",
                "bypass_and_continue",
            )
        )
        .strip()
        .lower(),
        result_cache_enabled=bool(
            getattr(settings, "AI_ROUTER_RESULT_CACHE_ENABLED", True)
        ),
        result_cache_mode=str(
            getattr(settings, "AI_ROUTER_RESULT_CACHE_MODE", "success_only")
        )
        .strip()
        .lower(),
        result_cache_ttl_success_s_by_request_class={
            REQUEST_CLASS_JOURNAL_ANALYSIS: max(
                5,
                int(
                    getattr(
                        settings,
                        "AI_ROUTER_RESULT_CACHE_SUCCESS_TTL_JOURNAL_SECONDS",
                        180,
                    )
                ),
            ),
            REQUEST_CLASS_COOLDOWN_REWRITE: max(
                5,
                int(
                    getattr(
                        settings,
                        "AI_ROUTER_RESULT_CACHE_SUCCESS_TTL_COOLDOWN_SECONDS",
                        45,
                    )
                ),
            ),
        },
        result_cache_ttl_failure_s=max(
            1,
            int(
                getattr(
                    settings,
                    "AI_ROUTER_RESULT_CACHE_FAILURE_TTL_SECONDS",
                    5,
                )
            ),
        ),
        redis_key_prefix=str(
            getattr(settings, "AI_ROUTER_REDIS_KEY_PREFIX", "haven:ai-router:")
        ),
        inflight_ttl_ms=max(
            100,
            int(getattr(settings, "AI_ROUTER_INFLIGHT_TTL_MS", 7000)),
        ),
        degraded_max_total_attempts=max(
            1,
            int(getattr(settings, "AI_ROUTER_DEGRADED_MAX_TOTAL_ATTEMPTS", 2)),
        ),
        degraded_disable_sleep=bool(
            getattr(settings, "AI_ROUTER_DEGRADED_DISABLE_SLEEP", True)
        ),
        degraded_disable_cache=bool(
            getattr(settings, "AI_ROUTER_DEGRADED_DISABLE_CACHE", True)
        ),
        degraded_disable_poll=bool(
            getattr(settings, "AI_ROUTER_DEGRADED_DISABLE_POLL", True)
        ),
        profile_candidates_by_request_class=default_candidates,
    )


def _normalize_policy(policy: AIRouterPolicy) -> AIRouterPolicy:
    jitter = (
        policy.backoff_jitter_mode
        if policy.backoff_jitter_mode in SUPPORTED_JITTER_MODES
        else "full"
    )
    duplicate_action = (
        policy.duplicate_exit_action
        if policy.duplicate_exit_action in SUPPORTED_DUPLICATE_EXIT_ACTIONS
        else "graceful_fallback"
    )
    mismatch_action = (
        policy.idempotency_mismatch_action
        if policy.idempotency_mismatch_action in SUPPORTED_IDEMPOTENCY_MISMATCH_ACTIONS
        else "bypass_and_continue"
    )
    mode = (
        policy.result_cache_mode
        if policy.result_cache_mode in {"success_only", "success_and_failure"}
        else "success_only"
    )
    return AIRouterPolicy(
        **{
            **policy.__dict__,
            "backoff_jitter_mode": jitter,
            "duplicate_exit_action": duplicate_action,
            "idempotency_mismatch_action": mismatch_action,
            "result_cache_mode": mode,
        }
    )


def _build_shared_state_store() -> AIRouterSharedStateStore:
    backend = str(getattr(settings, "AI_ROUTER_SHARED_STATE_BACKEND", "memory")).strip().lower()
    redis_url = (
        str(getattr(settings, "AI_ROUTER_REDIS_URL", "") or "").strip()
        or str(getattr(settings, "REDIS_URL", "") or "").strip()
        or str(getattr(settings, "ABUSE_GUARD_REDIS_URL", "") or "").strip()
    )
    key_prefix = str(getattr(settings, "AI_ROUTER_REDIS_KEY_PREFIX", "haven:ai-router:"))

    if backend == "redis" and redis_url:
        try:
            store = RedisAIRouterSharedStateStore(redis_url=redis_url, key_prefix=key_prefix)
            ai_router_runtime_metrics.set_state("shared_state_backend", "redis")
            ai_router_runtime_metrics.set_state("redis_degraded_mode", False)
            return store
        except Exception:
            ai_router_runtime_metrics.increment("ai_router_shared_state_redis_unavailable_total")
            ai_router_runtime_metrics.set_state("shared_state_backend", "memory")
            ai_router_runtime_metrics.set_state("redis_degraded_mode", True)
            return InMemoryAIRouterSharedStateStore(degraded_mode=True)

    ai_router_runtime_metrics.set_state("shared_state_backend", "memory")
    ai_router_runtime_metrics.set_state("redis_degraded_mode", backend == "redis")
    return InMemoryAIRouterSharedStateStore(degraded_mode=(backend == "redis"))


def _get_shared_state_store() -> AIRouterSharedStateStore:
    global _shared_state_store
    with _shared_state_lock:
        if _shared_state_store is None:
            _shared_state_store = _build_shared_state_store()
        return _shared_state_store


def reset_ai_router_runtime_state_for_tests() -> None:
    global _shared_state_store
    with _shared_state_lock:
        _shared_state_store = None
    ai_router_runtime_metrics.reset()


def resolve_idempotency_status(
    *,
    in_flight: bool,
    fingerprint_mismatch: bool,
) -> str:
    """Resolve idempotency outcome with deterministic precedence.

    Precedence is fixed to match the documented policy:
    1) in-flight conflict => 409 semantic
    2) same key but different fingerprint => 422 semantic
    3) otherwise => ok
    """
    if in_flight:
        return IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409
    if fingerprint_mismatch:
        return IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422
    return IDEMPOTENCY_STATUS_OK


def normalize_provider(provider_name: str | None) -> str:
    normalized = (provider_name or "").strip().lower()
    if normalized in SUPPORTED_PROVIDERS:
        return normalized
    return DEFAULT_PROVIDER


def normalize_router_task(task_name: str | None) -> str:
    normalized = (task_name or "").strip().lower()
    if normalized in SUPPORTED_ROUTER_TASKS:
        return normalized
    return TASK_L2_DEEP_REASONING


def normalize_request_class(request_class: str | None) -> str:
    normalized = (request_class or "").strip().lower()
    if normalized in SUPPORTED_REQUEST_CLASSES:
        return normalized
    return REQUEST_CLASS_JOURNAL_ANALYSIS


def normalize_idempotency_key(*, idempotency_key: str | None, request_id: str | None) -> str:
    return _normalize_idempotency_key(
        idempotency_key=idempotency_key,
        request_id=request_id,
    )


def build_normalized_content_hash(content: str) -> str:
    return _build_normalized_content_hash(content)


def _canonical_json_dumps(value: Any) -> str:
    return _canonical_json_dumps_from_identity(value)


def build_input_fingerprint(*, payload: dict[str, Any]) -> str:
    """Build deterministic fingerprint for cache/idempotency guard.

    The payload MUST contain structured JSON values only (no NaN/Infinity), and
    SHOULD include schema/prompt/moderation versions when available.
    """
    return _build_input_fingerprint(payload=payload)


def _build_route(
    *,
    primary_provider: str | None,
    valid_reason: str,
    normalized_reason: str,
) -> AIRoute:
    raw_primary = (primary_provider or "").strip().lower()
    provider_chain = build_provider_chain(
        primary_provider=primary_provider,
        fallback_provider=settings.AI_ROUTER_FALLBACK_PROVIDER,
        fallback_enabled=settings.AI_ROUTER_ENABLE_FALLBACK,
    )
    selected_provider = provider_chain[0]
    reason = valid_reason
    if raw_primary and raw_primary not in SUPPORTED_PROVIDERS:
        reason = normalized_reason

    return AIRoute(
        selected_provider=selected_provider,
        provider_chain=provider_chain,
        fallback_enabled=settings.AI_ROUTER_ENABLE_FALLBACK,
        reason=reason,
    )


def select_task_route(task_name: str | None) -> AIRoute:
    normalized_task = normalize_router_task(task_name)
    raw_task_name = (task_name or "").strip().lower()
    unknown_task = bool(raw_task_name and raw_task_name not in SUPPORTED_ROUTER_TASKS)

    if normalized_task == TASK_L1_CLASSIFY_EXTRACT:
        primary_provider = (
            settings.AI_ROUTER_L1_PRIMARY_PROVIDER
            or settings.AI_ROUTER_PRIMARY_PROVIDER
        )
        return _build_route(
            primary_provider=primary_provider,
            valid_reason="task_policy_l1",
            normalized_reason="task_policy_l1_primary_normalized_to_default",
        )

    primary_provider = settings.AI_ROUTER_L2_PRIMARY_PROVIDER or settings.AI_ROUTER_PRIMARY_PROVIDER
    if unknown_task:
        return _build_route(
            primary_provider=primary_provider,
            valid_reason="task_policy_unknown_normalized_to_l2",
            normalized_reason="task_policy_unknown_normalized_to_l2_primary_normalized_to_default",
        )
    return _build_route(
        primary_provider=primary_provider,
        valid_reason="task_policy_l2",
        normalized_reason="task_policy_l2_primary_normalized_to_default",
    )


def select_analysis_route() -> AIRoute:
    return _build_route(
        primary_provider=settings.AI_ROUTER_PRIMARY_PROVIDER,
        valid_reason="configured_primary",
        normalized_reason="primary_provider_normalized_to_default",
    )


def build_provider_chain(
    *,
    primary_provider: str | None,
    fallback_provider: str | None,
    fallback_enabled: bool,
) -> tuple[str, ...]:
    primary = normalize_provider(primary_provider)
    if not fallback_enabled:
        return (primary,)

    fallback = normalize_provider(fallback_provider)
    if fallback == primary:
        return (primary,)
    return (primary, fallback)


def _metric_key(kind: str, provider: str, reason: str | None = None, *, profile: str | None = None) -> str:
    return _metric_key_from_support(
        kind,
        provider,
        reason,
        profile=profile,
    )


def _decision_metric_key(*, request_class: str, profile: str, reason: str) -> str:
    return _decision_metric_key_from_support(
        request_class=request_class,
        profile=profile,
        reason=reason,
    )


def _now_monotonic() -> float:
    return time.monotonic()


def _resolve_profile_chain(
    *,
    route: AIRoute,
    request_context: AIRouterRequestContext,
    policy: AIRouterPolicy,
    store: AIRouterSharedStateStore,
) -> tuple[tuple[str, ...], str]:
    return _resolve_profile_chain_from_support(
        route=route,
        request_context=request_context,
        policy=policy,
        store=store,
        normalize_request_class=normalize_request_class,
        normalize_provider=normalize_provider,
        is_profile_on_cooldown=_is_profile_on_cooldown,
        metric_increment=ai_router_runtime_metrics.increment,
        metric_key_builder=_metric_key,
    )


def _retry_after_seconds(exc: AIProviderError) -> float | None:
    return _parse_retry_after_seconds_from_module(exc.retry_after_seconds)


def _compute_backoff_seconds(*, attempt: int, policy: AIRouterPolicy) -> float:
    return _compute_backoff_seconds_from_module(attempt=attempt, policy=policy)


def _elapsed_ms(*, start_monotonic: float, now_func: Callable[[], float]) -> int:
    return _elapsed_ms_from_helpers(start_monotonic=start_monotonic, now_func=now_func)


def _remaining_ms(*, start_monotonic: float, now_func: Callable[[], float], max_elapsed_ms: int) -> int:
    return _remaining_ms_from_helpers(
        start_monotonic=start_monotonic,
        now_func=now_func,
        max_elapsed_ms=max_elapsed_ms,
    )


def _make_router_key(*, request_context: AIRouterRequestContext, idempotency_key: str) -> str:
    return _make_router_key_from_helpers(
        request_context=request_context,
        idempotency_key=idempotency_key,
        normalize_request_class=normalize_request_class,
    )


def _result_cache_key(router_key: str) -> str:
    return _result_cache_key_from_helpers(router_key)


def _inflight_key(router_key: str) -> str:
    return _inflight_key_from_helpers(router_key)


def _schema_fail_counter_key(*, request_class: str, profile: str) -> str:
    return _schema_fail_counter_key_from_helpers(
        request_class=request_class,
        profile=profile,
    )


def _schema_cooldown_key(*, request_class: str, profile: str) -> str:
    return _schema_cooldown_key_from_helpers(
        request_class=request_class,
        profile=profile,
    )


def _serialize_parsed(parsed: Any) -> dict[str, Any]:
    return _serialize_parsed_from_support(parsed)


def _current_unix_ms() -> int:
    return _current_unix_ms_from_helpers()


def _result_from_cache_payload(
    *,
    cached_payload: dict[str, Any],
    idempotency_key: str,
) -> AIProviderRuntimeResult | None:
    return _result_from_cache_payload_from_support(
        cached_payload=cached_payload,
        idempotency_key=idempotency_key,
    )


def _build_cache_payload(
    *,
    request_context: AIRouterRequestContext,
    provider: str,
    model_version: str,
    parsed_payload: dict[str, Any],
    status: str,
    gate_decision_hash: str | None,
) -> dict[str, Any]:
    return _build_cache_payload_from_support(
        request_context=request_context,
        provider=provider,
        model_version=model_version,
        parsed_payload=parsed_payload,
        status=status,
        gate_decision_hash=gate_decision_hash,
        current_unix_ms=_current_unix_ms,
        normalize_request_class=normalize_request_class,
    )


def _is_profile_on_cooldown(
    *,
    store: AIRouterSharedStateStore,
    request_class: str,
    profile: str,
) -> bool:
    return _is_profile_on_cooldown_from_support(
        store=store,
        request_class=request_class,
        profile=profile,
        current_unix_ms=_current_unix_ms,
        get_cooldown_until_ms=_get_cooldown_until_ms,
    )


def _mark_profile_cooldown(
    *,
    store: AIRouterSharedStateStore,
    request_class: str,
    profile: str,
    cooldown_seconds: int,
) -> None:
    _mark_profile_cooldown_from_support(
        store=store,
        request_class=request_class,
        profile=profile,
        cooldown_seconds=cooldown_seconds,
        current_unix_ms=_current_unix_ms,
        schema_cooldown_key_builder=_schema_cooldown_key,
    )


def _get_cooldown_until_ms(*, store: AIRouterSharedStateStore, request_class: str, profile: str) -> int:
    return _get_cooldown_until_ms_from_support(
        store=store,
        request_class=request_class,
        profile=profile,
        schema_cooldown_key_builder=_schema_cooldown_key,
    )


def _record_schema_failure(
    *,
    store: AIRouterSharedStateStore,
    request_class: str,
    profile: str,
    policy: AIRouterPolicy,
) -> bool:
    return _record_schema_failure_from_support(
        store=store,
        request_class=request_class,
        profile=profile,
        policy=policy,
        schema_fail_counter_key_builder=_schema_fail_counter_key,
        mark_profile_cooldown=_mark_profile_cooldown,
        metric_increment=ai_router_runtime_metrics.increment,
    )


def _get_result_cache_ttl(
    *,
    policy: AIRouterPolicy,
    request_class: str,
    status: str,
) -> int:
    return _get_result_cache_ttl_from_support(
        policy=policy,
        request_class=request_class,
        status=status,
    )


def _sleep_disabled(*, policy: AIRouterPolicy, store: AIRouterSharedStateStore) -> bool:
    return _sleep_disabled_from_support(policy=policy, store=store)


async def run_provider_adapters(
    *,
    route: AIRoute,
    adapters: dict[str, AIProviderAdapter],
    request_context: AIRouterRequestContext | None = None,
    policy_override: AIRouterPolicy | None = None,
    shared_state_store: AIRouterSharedStateStore | None = None,
    sleep_func: Callable[[float], Awaitable[None]] = asyncio.sleep,
    now_func: Callable[[], float] = _now_monotonic,
) -> AIProviderRuntimeResult:
    request_context = request_context or AIRouterRequestContext()
    policy = _normalize_policy(policy_override or _load_policy())
    store = shared_state_store or _get_shared_state_store()

    ai_router_runtime_metrics.set_state("shared_state_backend", store.backend_name)
    ai_router_runtime_metrics.set_state("redis_degraded_mode", store.degraded_mode)

    if store.degraded_mode:
        ai_router_runtime_metrics.increment("ai_router_degraded_mode_total")

    request_class = normalize_request_class(request_context.request_class)
    max_elapsed_ms = max(200, policy.max_elapsed_ms)
    max_total_attempts = policy.max_total_attempts
    max_attempts_per_profile = policy.max_attempts_per_profile
    if store.degraded_mode:
        max_total_attempts = max(1, policy.degraded_max_total_attempts)
        max_attempts_per_profile = 1

    idempotency_key = normalize_idempotency_key(
        idempotency_key=request_context.idempotency_key,
        request_id=request_context.request_id,
    )
    router_key = _make_router_key(request_context=request_context, idempotency_key=idempotency_key)

    cache_enabled = bool(policy.result_cache_enabled)
    poll_enabled = True
    enforce_cooldown = True
    if store.degraded_mode:
        if policy.degraded_disable_cache:
            cache_enabled = False
        if policy.degraded_disable_poll:
            poll_enabled = False
        enforce_cooldown = False
        ai_router_runtime_metrics.increment("ai_router_redis_fallback_disabled_caches_total")

    cache_key = _result_cache_key(router_key)
    if cache_enabled:
        cached_payload = store.get_json(cache_key)
        if isinstance(cached_payload, dict):
            if _matches_input_fingerprint(request_context=request_context, cached_payload=cached_payload):
                cache_result = _result_from_cache_payload(
                    cached_payload=cached_payload,
                    idempotency_key=idempotency_key,
                )
                if cache_result is not None:
                    provider = cache_result.provider
                    ai_router_runtime_metrics.increment(
                        _metric_key("cache_hit", provider, profile=provider)
                    )
                    ai_router_runtime_metrics.increment(
                        _decision_metric_key(
                            request_class=request_class,
                            profile=provider,
                            reason="cache_hit",
                        )
                    )
                    return cache_result
            else:
                ai_router_runtime_metrics.increment("ai_router_cache_fingerprint_mismatch_total")
                ai_router_runtime_metrics.increment(
                    _metric_key("cache_miss", "unknown", "fingerprint_mismatch", profile="unknown")
                )
                status = resolve_idempotency_status(
                    in_flight=False,
                    fingerprint_mismatch=True,
                )
                if (
                    status == IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422
                    and policy.idempotency_mismatch_action == "reject"
                ):
                    raise AIProviderIdempotencyRejectedError(
                        idempotency_key=idempotency_key,
                        reason=status,
                    )

    start = now_func()
    inflight_key = _inflight_key(router_key)
    inflight_token = uuid.uuid4().hex

    lock_ttl_ms = max(policy.inflight_ttl_ms, max_elapsed_ms + 250)
    has_lock = store.reserve_inflight(
        inflight_key,
        token=inflight_token,
        ttl_ms=lock_ttl_ms,
    )

    if not has_lock:
        ai_router_runtime_metrics.increment("ai_router_inflight_duplicate_total")
        status = resolve_idempotency_status(
            in_flight=True,
            fingerprint_mismatch=False,
        )
        remaining_ms = _remaining_ms(start_monotonic=start, now_func=now_func, max_elapsed_ms=max_elapsed_ms)
        if (
            not poll_enabled
            or remaining_ms <= policy.duplicate_fast_yield_remaining_budget_ms
        ):
            ai_router_runtime_metrics.increment(
                _metric_key("failure", "unknown", "max_elapsed_exceeded_poll", profile="unknown")
            )
            if status == IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409:
                raise AIProviderFallbackExhaustedError(
                    chain=("inflight",),
                    failures=(
                        AIProviderAttemptFailure(
                            provider="inflight",
                            reason="max_elapsed_exceeded_poll",
                            retryable=False,
                        ),
                    ),
                )

        miss_count = 0
        while poll_enabled:
            cached_payload = store.get_json(cache_key) if cache_enabled else None
            if isinstance(cached_payload, dict) and _matches_input_fingerprint(
                request_context=request_context,
                cached_payload=cached_payload,
            ):
                cache_result = _result_from_cache_payload(
                    cached_payload=cached_payload,
                    idempotency_key=idempotency_key,
                )
                if cache_result is not None:
                    ai_router_runtime_metrics.increment("ai_router_duplicate_poll_hit_total")
                    return cache_result

            miss_count += 1
            if miss_count >= policy.duplicate_poll_max_consecutive_miss:
                ai_router_runtime_metrics.increment(
                    _metric_key("failure", "unknown", "poll_exhausted_no_result", profile="unknown")
                )
                break

            delay_ms = policy.duplicate_poll_interval_ms
            if policy.duplicate_poll_jitter_ms_max > 0:
                delay_ms += random.randint(0, policy.duplicate_poll_jitter_ms_max)

            remaining_ms = _remaining_ms(start_monotonic=start, now_func=now_func, max_elapsed_ms=max_elapsed_ms)
            if delay_ms > remaining_ms:
                ai_router_runtime_metrics.increment(
                    _metric_key("failure", "unknown", "max_elapsed_exceeded_poll", profile="unknown")
                )
                break

            if _sleep_disabled(policy=policy, store=store):
                break
            await sleep_func(delay_ms / 1000.0)

        raise AIProviderFallbackExhaustedError(
            chain=("inflight",),
            failures=(
                AIProviderAttemptFailure(
                    provider="inflight",
                    reason="poll_exhausted_no_result",
                    retryable=False,
                ),
            ),
        )

    try:
        profile_chain, decision_reason = _resolve_profile_chain(
            route=route,
            request_context=request_context,
            policy=policy,
            store=store,
        )

        failures: list[AIProviderAttemptFailure] = []
        total_attempts = 0

        for profile_index, profile in enumerate(profile_chain):
            provider = PROFILE_PROVIDER_MAP.get(profile)
            if not provider:
                continue
            if enforce_cooldown and _is_profile_on_cooldown(
                store=store,
                request_class=request_class,
                profile=profile,
            ):
                failures.append(
                    AIProviderAttemptFailure(
                        provider=provider,
                        reason="cooldown_active",
                        retryable=False,
                    )
                )
                ai_router_runtime_metrics.increment(
                    _metric_key("failure", provider, "cooldown_active", profile=profile)
                )
                continue

            adapter = adapters.get(provider)
            if adapter is None:
                failures.append(
                    AIProviderAttemptFailure(
                        provider=provider,
                        reason="provider_adapter_missing",
                        retryable=True,
                    )
                )
                ai_router_runtime_metrics.increment(
                    _metric_key(
                        "failure",
                        provider,
                        "provider_adapter_missing",
                        profile=profile,
                    )
                )
                if profile_index < len(profile_chain) - 1:
                    ai_router_runtime_metrics.increment("ai_router_fallback_activated_total")
                continue

            per_profile_attempt = 0
            while per_profile_attempt < max_attempts_per_profile:
                per_profile_attempt += 1
                total_attempts += 1

                if total_attempts > max_total_attempts:
                    failures.append(
                        AIProviderAttemptFailure(
                            provider=provider,
                            reason="max_elapsed_exceeded",
                            retryable=False,
                        )
                    )
                    ai_router_runtime_metrics.increment(
                        _metric_key("failure", provider, "max_elapsed_exceeded", profile=profile)
                    )
                    break

                if _remaining_ms(start_monotonic=start, now_func=now_func, max_elapsed_ms=max_elapsed_ms) <= 0:
                    failures.append(
                        AIProviderAttemptFailure(
                            provider=provider,
                            reason="max_elapsed_exceeded",
                            retryable=False,
                        )
                    )
                    ai_router_runtime_metrics.increment(
                        _metric_key("failure", provider, "max_elapsed_exceeded", profile=profile)
                    )
                    break

                try:
                    parsed, model_version = await adapter.run()
                except AIProviderError as exc:
                    reason = _reason_metric_bucket(exc.reason)
                    retryable = bool(exc.retryable)
                    failure = AIProviderAttemptFailure(
                        provider=provider,
                        reason=reason,
                        retryable=retryable,
                    )
                    failures.append(failure)
                    ai_router_runtime_metrics.record_attempt(success=False)
                    ai_router_runtime_metrics.increment(
                        _metric_key("failure", provider, reason, profile=profile)
                    )

                    if reason == "schema_validation_failed":
                        _record_schema_failure(
                            store=store,
                            request_class=request_class,
                            profile=profile,
                            policy=policy,
                        )

                    retry_after = _retry_after_seconds(exc)
                    should_failover = False
                    should_sleep = False
                    delay_seconds = 0.0

                    if reason == "status_429":
                        if retry_after is None:
                            ai_router_runtime_metrics.increment(
                                _metric_key(
                                    "failure",
                                    provider,
                                    "rate_limited_no_retry_after",
                                    profile=profile,
                                )
                            )
                            delay_seconds = _compute_backoff_seconds(
                                attempt=per_profile_attempt,
                                policy=policy,
                            )
                            should_sleep = retryable and (per_profile_attempt < max_attempts_per_profile)
                        else:
                            if retry_after > policy.rate_limit_failover_threshold_seconds:
                                should_failover = True
                                ai_router_runtime_metrics.increment(
                                    _metric_key(
                                        "failure",
                                        provider,
                                        "retry_after_exceeds_threshold",
                                        profile=profile,
                                    )
                                )
                                _mark_profile_cooldown(
                                    store=store,
                                    request_class=request_class,
                                    profile=profile,
                                    cooldown_seconds=max(1, int(retry_after)),
                                )
                            else:
                                should_sleep = retryable and (per_profile_attempt < max_attempts_per_profile)
                                delay_seconds = max(
                                    retry_after,
                                    _compute_backoff_seconds(
                                        attempt=per_profile_attempt,
                                        policy=policy,
                                    ),
                                )
                                ai_router_runtime_metrics.increment(
                                    _metric_key(
                                        "failure",
                                        provider,
                                        "retry_after_retry",
                                        profile=profile,
                                    )
                                )
                    elif retryable and per_profile_attempt < max_attempts_per_profile:
                        should_sleep = True
                        delay_seconds = _compute_backoff_seconds(
                            attempt=per_profile_attempt,
                            policy=policy,
                        )
                        ai_router_runtime_metrics.increment(
                            _metric_key(
                                "failure",
                                provider,
                                "retry_backoff_retry",
                                profile=profile,
                            )
                        )
                    else:
                        should_failover = True

                    if should_sleep and not _sleep_disabled(policy=policy, store=store):
                        remaining_ms = _remaining_ms(
                            start_monotonic=start,
                            now_func=now_func,
                            max_elapsed_ms=max_elapsed_ms,
                        )
                        wait_ms = int(delay_seconds * 1000.0)
                        if wait_ms > 0 and wait_ms <= remaining_ms:
                            await sleep_func(wait_ms / 1000.0)
                        else:
                            should_failover = True

                    if should_failover:
                        break

                    continue
                except (asyncio.TimeoutError, TimeoutError):
                    failure = AIProviderAttemptFailure(
                        provider=provider,
                        reason="timeout",
                        retryable=True,
                    )
                    failures.append(failure)
                    ai_router_runtime_metrics.record_attempt(success=False)
                    ai_router_runtime_metrics.increment(
                        _metric_key("failure", provider, failure.reason, profile=profile)
                    )
                    if per_profile_attempt < max_attempts_per_profile and not _sleep_disabled(
                        policy=policy,
                        store=store,
                    ):
                        delay_seconds = _compute_backoff_seconds(
                            attempt=per_profile_attempt,
                            policy=policy,
                        )
                        remaining_ms = _remaining_ms(
                            start_monotonic=start,
                            now_func=now_func,
                            max_elapsed_ms=max_elapsed_ms,
                        )
                        wait_ms = int(delay_seconds * 1000.0)
                        if wait_ms > 0 and wait_ms <= remaining_ms:
                            await sleep_func(wait_ms / 1000.0)
                            continue
                    break
                except Exception:
                    failure = AIProviderAttemptFailure(
                        provider=provider,
                        reason="unexpected_error",
                        retryable=True,
                    )
                    failures.append(failure)
                    ai_router_runtime_metrics.record_attempt(success=False)
                    ai_router_runtime_metrics.increment(
                        _metric_key("failure", provider, failure.reason, profile=profile)
                    )
                    if per_profile_attempt < max_attempts_per_profile and not _sleep_disabled(
                        policy=policy,
                        store=store,
                    ):
                        delay_seconds = _compute_backoff_seconds(
                            attempt=per_profile_attempt,
                            policy=policy,
                        )
                        remaining_ms = _remaining_ms(
                            start_monotonic=start,
                            now_func=now_func,
                            max_elapsed_ms=max_elapsed_ms,
                        )
                        wait_ms = int(delay_seconds * 1000.0)
                        if wait_ms > 0 and wait_ms <= remaining_ms:
                            await sleep_func(wait_ms / 1000.0)
                            continue
                    break

                parsed_payload = _serialize_parsed(parsed)
                ai_router_runtime_metrics.record_attempt(success=True)
                ai_router_runtime_metrics.increment(
                    _metric_key("success", provider, profile=profile)
                )
                ai_router_runtime_metrics.increment(
                    _decision_metric_key(
                        request_class=request_class,
                        profile=profile,
                        reason=decision_reason,
                    )
                )

                if cache_enabled and _is_cache_eligible_success(
                    request_context=request_context,
                    parsed_payload=parsed_payload,
                ):
                    ttl_seconds = _get_result_cache_ttl(
                        policy=policy,
                        request_class=request_class,
                        status=_RESULT_CACHE_STATUS_SUCCESS,
                    )
                    store.set_json(
                        cache_key,
                        _build_cache_payload(
                            request_context=request_context,
                            provider=provider,
                            model_version=model_version,
                            parsed_payload=parsed_payload,
                            status=_RESULT_CACHE_STATUS_SUCCESS,
                            gate_decision_hash=request_context.gate_decision_hash,
                        ),
                        ttl_seconds=ttl_seconds,
                    )

                fallback_used = profile_index > 0
                if fallback_used:
                    ai_router_runtime_metrics.increment("ai_router_fallback_success_total")

                return AIProviderRuntimeResult(
                    provider=provider,
                    model_version=model_version,
                    parsed=parsed,
                    fallback_used=fallback_used,
                    failures=tuple(failures),
                    cache_hit=False,
                    idempotency_key=idempotency_key,
                    decision_reason=decision_reason,
                )

            if profile_index < len(profile_chain) - 1:
                ai_router_runtime_metrics.increment("ai_router_fallback_activated_total")

        if cache_enabled and policy.result_cache_mode == "success_and_failure" and failures:
            last_failure = failures[-1]
            if _is_failure_cacheable(failure=last_failure):
                ttl_seconds = _get_result_cache_ttl(
                    policy=policy,
                    request_class=request_class,
                    status=_RESULT_CACHE_STATUS_FAILURE,
                )
                store.set_json(
                    cache_key,
                    _build_cache_payload(
                        request_context=request_context,
                        provider=last_failure.provider,
                        model_version="",
                        parsed_payload={"failure_reason": last_failure.reason},
                        status=_RESULT_CACHE_STATUS_FAILURE,
                        gate_decision_hash=request_context.gate_decision_hash,
                    ),
                    ttl_seconds=ttl_seconds,
                )

        ai_router_runtime_metrics.increment("ai_router_provider_exhausted_total")
        raise AIProviderFallbackExhaustedError(
            chain=tuple(PROFILE_PROVIDER_MAP.get(profile, "unknown") for profile in profile_chain),
            failures=tuple(failures),
        )
    finally:
        store.release_inflight(
            inflight_key,
            token=inflight_token,
        )
