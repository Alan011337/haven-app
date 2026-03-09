import sys
import unittest
from pathlib import Path
import time
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_router import (  # noqa: E402
    AIProviderAdapter,
    AIProviderError,
    AIProviderFallbackExhaustedError,
    AIRoute,
    AIRouterPolicy,
    AIRouterRequestContext,
    IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422,
    IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409,
    InMemoryAIRouterSharedStateStore,
    REQUEST_CLASS_JOURNAL_ANALYSIS,
    ai_router_runtime_metrics,
    build_ai_router_runtime_payload,
    build_input_fingerprint,
    resolve_idempotency_status,
    run_provider_adapters,
)


class AIRouterRuntimeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        ai_router_runtime_metrics.reset()

    def _policy(self) -> AIRouterPolicy:
        return AIRouterPolicy(
            free_tier_first_enabled=True,
            max_attempts_per_profile=2,
            max_total_attempts=4,
            max_elapsed_ms=3000,
            backoff_base_ms=50,
            backoff_max_ms=250,
            backoff_jitter_mode="none",
            rate_limit_failover_threshold_seconds=2.0,
            duplicate_poll_interval_ms=20,
            duplicate_poll_jitter_ms_max=0,
            duplicate_poll_max_consecutive_miss=2,
            duplicate_fast_yield_remaining_budget_ms=100,
            duplicate_exit_action="graceful_fallback",
            schema_fail_cooldown_threshold=2,
            schema_fail_window_seconds=60,
            schema_fail_cooldown_seconds=120,
            idempotency_mismatch_action="bypass_and_continue",
            result_cache_enabled=True,
            result_cache_mode="success_only",
            result_cache_ttl_success_s_by_request_class={
                "journal_analysis": 60,
                "cooldown_rewrite": 30,
            },
            result_cache_ttl_failure_s=5,
            redis_key_prefix="haven:ai-router:",
            inflight_ttl_ms=5000,
            degraded_max_total_attempts=1,
            degraded_disable_sleep=True,
            degraded_disable_cache=True,
            degraded_disable_poll=True,
            profile_candidates_by_request_class={
                "journal_analysis": ("gemini_free", "openai_cheap"),
                "cooldown_rewrite": ("gemini_free",),
            },
        )

    async def test_idempotency_status_precedence_inflight_before_fingerprint_mismatch(self) -> None:
        status = resolve_idempotency_status(
            in_flight=True,
            fingerprint_mismatch=True,
        )
        self.assertEqual(status, IDEMPOTENCY_STATUS_INFLIGHT_CONFLICT_409)

        mismatch_only = resolve_idempotency_status(
            in_flight=False,
            fingerprint_mismatch=True,
        )
        self.assertEqual(mismatch_only, IDEMPOTENCY_STATUS_FINGERPRINT_MISMATCH_422)

    async def test_timeout_failure_falls_back_to_next_provider(self) -> None:
        async def gemini_timeout() -> tuple[dict[str, Any], str]:
            raise AIProviderError(provider="gemini", reason="timeout", retryable=True)

        async def openai_success() -> tuple[dict[str, Any], str]:
            return {"ok": True, "safety_tier": 0}, "gpt-4o-mini"

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )
        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_timeout),
            "openai": AIProviderAdapter(provider="openai", run=openai_success),
        }

        result = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=AIRouterRequestContext(request_class="journal_analysis"),
            policy_override=self._policy(),
            shared_state_store=InMemoryAIRouterSharedStateStore(),
        )
        self.assertEqual(result.provider, "openai")
        self.assertTrue(result.fallback_used)

        snapshot = ai_router_runtime_metrics.snapshot()
        self.assertEqual(snapshot.get("ai_router_fallback_activated_total"), 1)
        self.assertEqual(snapshot.get("ai_router_fallback_success_total"), 1)

    async def test_rate_limit_with_retry_after_above_threshold_fails_over_without_sleep(self) -> None:
        sleep_calls: list[float] = []

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        async def gemini_rate_limited() -> tuple[dict[str, Any], str]:
            raise AIProviderError(
                provider="gemini",
                reason="status_429",
                retryable=True,
                status_code=429,
                retry_after_seconds=5.0,
            )

        async def openai_success() -> tuple[dict[str, Any], str]:
            return {"ok": True, "safety_tier": 0}, "gpt-4o-mini"

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )
        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_rate_limited),
            "openai": AIProviderAdapter(provider="openai", run=openai_success),
        }

        result = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=AIRouterRequestContext(request_class="journal_analysis"),
            policy_override=self._policy(),
            shared_state_store=InMemoryAIRouterSharedStateStore(),
            sleep_func=fake_sleep,
        )
        self.assertEqual(result.provider, "openai")
        self.assertEqual(sleep_calls, [])

    async def test_rate_limit_with_short_retry_after_retries_once(self) -> None:
        sleep_calls: list[float] = []
        attempts = {"gemini": 0}

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        async def gemini_then_success() -> tuple[dict[str, Any], str]:
            attempts["gemini"] += 1
            if attempts["gemini"] == 1:
                raise AIProviderError(
                    provider="gemini",
                    reason="status_429",
                    retryable=True,
                    status_code=429,
                    retry_after_seconds=0.2,
                )
            return {"ok": True, "safety_tier": 0}, "gemini-2.0-flash-lite"

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )
        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_then_success),
            "openai": AIProviderAdapter(
                provider="openai",
                run=lambda: (_ for _ in ()).throw(RuntimeError("should_not_call")),
            ),
        }

        result = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=AIRouterRequestContext(request_class="journal_analysis"),
            policy_override=self._policy(),
            shared_state_store=InMemoryAIRouterSharedStateStore(),
            sleep_func=fake_sleep,
        )
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(attempts["gemini"], 2)
        self.assertEqual(len(sleep_calls), 1)
        self.assertGreaterEqual(sleep_calls[0], 0.2)

    async def test_result_cache_hit_with_matching_fingerprint(self) -> None:
        store = InMemoryAIRouterSharedStateStore()
        fingerprint = build_input_fingerprint(payload={"request_class": "journal_analysis", "v": 1})
        context = AIRouterRequestContext(
            request_class=REQUEST_CLASS_JOURNAL_ANALYSIS,
            request_id="req-cache-hit",
            idempotency_key="idem-cache-hit",
            input_fingerprint=fingerprint,
            strict_schema_mode=True,
        )

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )

        call_count = {"gemini": 0}

        async def gemini_success() -> tuple[dict[str, Any], str]:
            call_count["gemini"] += 1
            return {"ok": True, "safety_tier": 0}, "gemini-2.0-flash-lite"

        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_success),
            "openai": AIProviderAdapter(provider="openai", run=gemini_success),
        }

        first = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=context,
            policy_override=self._policy(),
            shared_state_store=store,
        )
        second = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=context,
            policy_override=self._policy(),
            shared_state_store=store,
        )

        self.assertFalse(first.cache_hit)
        self.assertTrue(second.cache_hit)
        self.assertEqual(call_count["gemini"], 1)

    async def test_result_cache_fingerprint_mismatch_bypasses_cache(self) -> None:
        store = InMemoryAIRouterSharedStateStore()
        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )
        calls = {"count": 0}

        async def gemini_success() -> tuple[dict[str, Any], str]:
            calls["count"] += 1
            return {"ok": True, "safety_tier": 0}, "gemini-2.0-flash-lite"

        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_success),
        }

        context1 = AIRouterRequestContext(
            request_class=REQUEST_CLASS_JOURNAL_ANALYSIS,
            request_id="req-a",
            idempotency_key="same-idem-key",
            input_fingerprint=build_input_fingerprint(payload={"request_class": "journal_analysis", "hash": "a"}),
        )
        context2 = AIRouterRequestContext(
            request_class=REQUEST_CLASS_JOURNAL_ANALYSIS,
            request_id="req-b",
            idempotency_key="same-idem-key",
            input_fingerprint=build_input_fingerprint(payload={"request_class": "journal_analysis", "hash": "b"}),
        )

        await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=context1,
            policy_override=self._policy(),
            shared_state_store=store,
        )
        await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=context2,
            policy_override=self._policy(),
            shared_state_store=store,
        )

        self.assertEqual(calls["count"], 2)
        snapshot = ai_router_runtime_metrics.snapshot()
        self.assertEqual(snapshot.get("ai_router_cache_fingerprint_mismatch_total"), 1)

    async def test_schema_validation_failures_trigger_cooldown_and_skip_profile(self) -> None:
        store = InMemoryAIRouterSharedStateStore()
        policy = self._policy()

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )

        async def gemini_schema_fail() -> tuple[dict[str, Any], str]:
            raise AIProviderError(provider="gemini", reason="schema_validation_failed", retryable=True)

        async def openai_success() -> tuple[dict[str, Any], str]:
            return {"ok": True, "safety_tier": 0}, "gpt-4o-mini"

        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_schema_fail),
            "openai": AIProviderAdapter(provider="openai", run=openai_success),
        }

        # first run: schema failure count increments but not yet cooled down
        await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=AIRouterRequestContext(request_class=REQUEST_CLASS_JOURNAL_ANALYSIS),
            policy_override=policy,
            shared_state_store=store,
        )

        # second run should trip cooldown and skip gemini directly.
        result = await run_provider_adapters(
            route=route,
            adapters=adapters,
            request_context=AIRouterRequestContext(request_class=REQUEST_CLASS_JOURNAL_ANALYSIS),
            policy_override=policy,
            shared_state_store=store,
        )

        self.assertEqual(result.provider, "openai")
        snapshot = ai_router_runtime_metrics.snapshot()
        self.assertGreaterEqual(snapshot.get("ai_router_schema_cooldown_activated_total", 0), 1)

    async def test_degraded_mode_disables_sleep_even_on_retryable_failures(self) -> None:
        sleep_calls: list[float] = []
        degraded_store = InMemoryAIRouterSharedStateStore(degraded_mode=True)

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        async def gemini_fail() -> tuple[dict[str, Any], str]:
            raise AIProviderError(provider="gemini", reason="timeout", retryable=True)

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini",),
            fallback_enabled=False,
            reason="configured_primary",
        )
        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_fail),
        }

        with self.assertRaises(AIProviderFallbackExhaustedError):
            await run_provider_adapters(
                route=route,
                adapters=adapters,
                request_context=AIRouterRequestContext(request_class=REQUEST_CLASS_JOURNAL_ANALYSIS),
                policy_override=self._policy(),
                shared_state_store=degraded_store,
                sleep_func=fake_sleep,
            )

        self.assertEqual(sleep_calls, [])

    async def test_runtime_payload_exposes_router_burn_rate_windows(self) -> None:
        now_ts = time.time()
        for _ in range(90):
            ai_router_runtime_metrics.record_attempt(success=False, now_ts=now_ts)
        for _ in range(30):
            ai_router_runtime_metrics.record_attempt(success=True, now_ts=now_ts)
        payload = build_ai_router_runtime_payload()
        self.assertIn("burn_rate", payload)
        burn_rate = payload["burn_rate"]
        self.assertEqual(burn_rate.get("status"), "degraded")
        fast_window = burn_rate.get("fast_window") or {}
        slow_window = burn_rate.get("slow_window") or {}
        self.assertGreater(fast_window.get("attempts_total", 0), 0)
        self.assertGreater(slow_window.get("attempts_total", 0), 0)
        self.assertIn("burn_rate", fast_window)
        self.assertIn("burn_rate", slow_window)

    async def test_degraded_mode_never_calls_sleep_zero_or_positive(self) -> None:
        sleep_calls: list[float] = []
        degraded_store = InMemoryAIRouterSharedStateStore(degraded_mode=True)

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        async def gemini_fail() -> tuple[dict[str, Any], str]:
            raise AIProviderError(provider="gemini", reason="status_429", retryable=True)

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini",),
            fallback_enabled=False,
            reason="configured_primary",
        )
        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_fail),
        }

        with self.assertRaises(AIProviderFallbackExhaustedError):
            await run_provider_adapters(
                route=route,
                adapters=adapters,
                request_context=AIRouterRequestContext(request_class=REQUEST_CLASS_JOURNAL_ANALYSIS),
                policy_override=self._policy(),
                shared_state_store=degraded_store,
                sleep_func=fake_sleep,
            )

        self.assertEqual(sleep_calls, [])


if __name__ == "__main__":
    unittest.main()
