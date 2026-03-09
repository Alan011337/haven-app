import hashlib
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import ai_router as ai_router_module  # noqa: E402
from app.services.ai_router import (  # noqa: E402
    AIProviderAdapter,
    AIProviderError,
    AIProviderFallbackExhaustedError,
    AIRoute,
    AIRouterPolicy,
    AIRouterRequestContext,
    InMemoryAIRouterSharedStateStore,
    REQUEST_CLASS_JOURNAL_ANALYSIS,
    run_provider_adapters,
)


def _policy() -> AIRouterPolicy:
    return AIRouterPolicy(
        free_tier_first_enabled=True,
        max_attempts_per_profile=2,
        max_total_attempts=4,
        max_elapsed_ms=3000,
        backoff_base_ms=100,
        backoff_max_ms=300,
        backoff_jitter_mode="none",
        rate_limit_failover_threshold_seconds=2.0,
        duplicate_poll_interval_ms=20,
        duplicate_poll_jitter_ms_max=0,
        duplicate_poll_max_consecutive_miss=3,
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


class AIRouterDegradedChaosTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        ai_router_module.reset_ai_router_runtime_state_for_tests()

    async def test_shared_state_falls_back_to_memory_when_redis_unavailable(self) -> None:
        with patch.object(ai_router_module.settings, "AI_ROUTER_SHARED_STATE_BACKEND", "redis"), patch.object(
            ai_router_module.settings,
            "AI_ROUTER_REDIS_URL",
            "redis://127.0.0.1:6379/0",
        ), patch.object(
            ai_router_module,
            "RedisAIRouterSharedStateStore",
            side_effect=RuntimeError("redis unavailable"),
        ):
            store = ai_router_module._get_shared_state_store()

        self.assertEqual(store.backend_name, "memory")
        self.assertTrue(store.degraded_mode)
        snapshot = ai_router_module.ai_router_runtime_metrics.snapshot()
        self.assertGreaterEqual(snapshot.get("ai_router_shared_state_redis_unavailable_total", 0), 1)
        state = ai_router_module.ai_router_runtime_metrics.state_snapshot()
        self.assertEqual(state.get("shared_state_backend"), "memory")
        self.assertEqual(state.get("redis_degraded_mode"), True)

    async def test_degraded_mode_duplicate_conflict_skips_cache_and_poll_paths(self) -> None:
        store = InMemoryAIRouterSharedStateStore(degraded_mode=True)
        context = AIRouterRequestContext(
            request_class=REQUEST_CLASS_JOURNAL_ANALYSIS,
            request_id="req-chaos-001",
            idempotency_key="idem-chaos-0001",
            subject_key="user-chaos",
        )
        router_key = hashlib.sha256(
            "v1:user-chaos:journal_analysis:idem-chaos-0001".encode("utf-8")
        ).hexdigest()
        store.set_json(
            f"result:{router_key}",
            {
                "provider": "gemini",
                "model_version": "gemini-2.0-flash-lite",
                "parsed_payload": {"ok": True, "safety_tier": 0},
                "input_fingerprint": None,
            },
            ttl_seconds=60,
        )
        store.reserve_inflight(f"inflight:{router_key}", token="owned-by-other", ttl_ms=4000)

        sleep_calls: list[float] = []
        adapter_calls = {"count": 0}

        async def fake_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        async def gemini_success() -> tuple[dict[str, Any], str]:
            adapter_calls["count"] += 1
            return {"ok": True, "safety_tier": 0}, "gemini-2.0-flash-lite"

        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini",),
            fallback_enabled=False,
            reason="configured_primary",
        )
        adapters = {"gemini": AIProviderAdapter(provider="gemini", run=gemini_success)}

        with self.assertRaises(AIProviderFallbackExhaustedError):
            await run_provider_adapters(
                route=route,
                adapters=adapters,
                request_context=context,
                policy_override=_policy(),
                shared_state_store=store,
                sleep_func=fake_sleep,
            )

        self.assertEqual(adapter_calls["count"], 0)
        self.assertEqual(sleep_calls, [])
        snapshot = ai_router_module.ai_router_runtime_metrics.snapshot()
        self.assertGreaterEqual(snapshot.get("ai_router_inflight_duplicate_total", 0), 1)
        self.assertGreaterEqual(snapshot.get("ai_router_redis_fallback_disabled_caches_total", 0), 1)

    async def test_degraded_mode_disables_shared_schema_cooldown_enforcement(self) -> None:
        store = InMemoryAIRouterSharedStateStore(degraded_mode=True)
        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini",),
            fallback_enabled=False,
            reason="configured_primary",
        )

        async def gemini_schema_fail() -> tuple[dict[str, Any], str]:
            raise AIProviderError(provider="gemini", reason="schema_validation_failed", retryable=True)

        adapters = {"gemini": AIProviderAdapter(provider="gemini", run=gemini_schema_fail)}

        with self.assertRaises(AIProviderFallbackExhaustedError):
            await run_provider_adapters(
                route=route,
                adapters=adapters,
                request_context=AIRouterRequestContext(request_class=REQUEST_CLASS_JOURNAL_ANALYSIS),
                policy_override=_policy(),
                shared_state_store=store,
            )

        snapshot = ai_router_module.ai_router_runtime_metrics.snapshot()
        self.assertGreaterEqual(snapshot.get("ai_router_schema_cooldown_disabled_redis_down_total", 0), 1)


if __name__ == "__main__":
    unittest.main()
