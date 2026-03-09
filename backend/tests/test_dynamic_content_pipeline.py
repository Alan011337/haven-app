from __future__ import annotations

import asyncio
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.models.card import Card, CardDeck  # noqa: E402
from app.services import dynamic_content_pipeline as pipeline  # noqa: E402
from app.services.dynamic_content_runtime_metrics import dynamic_content_runtime_metrics  # noqa: E402


class _FakeResponseMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class _FakeResponseChoice:
    def __init__(self, content: str) -> None:
        self.message = _FakeResponseMessage(content)


class _FakeResponse:
    def __init__(self, content: str) -> None:
        self.choices = [_FakeResponseChoice(content)]


class _FakeCompletions:
    def __init__(self, fn):
        self._fn = fn

    async def create(self, **kwargs):  # noqa: ANN003
        return await self._fn(**kwargs)


class _FakeChat:
    def __init__(self, fn):
        self.completions = _FakeCompletions(fn)


class _FakeAsyncOpenAI:
    def __init__(self, fn):
        self.chat = _FakeChat(fn)


class _FakeCooldownStore:
    supports_global_cleanup_scan = False

    def __init__(self) -> None:
        self.payload: dict | None = None

    def load(self, key: str):  # noqa: ARG002
        return self.payload

    def save(self, key: str, value: dict, *, ttl_seconds: int | None = None) -> None:  # noqa: ARG002
        self.payload = dict(value)

    def delete(self, key: str) -> None:  # noqa: ARG002
        self.payload = None

    def iter_keys(self):
        return []


class DynamicContentPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        dynamic_content_runtime_metrics.reset()
        pipeline._reset_cooldown_for_test()

    async def test_provider_timeout_falls_back(self) -> None:
        async def _always_timeout(**kwargs):  # noqa: ANN003
            raise asyncio.TimeoutError()

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_always_timeout)  # noqa: ARG005
        )
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_TIMEOUT_SECONDS", 1.0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_FAILURE_COOLDOWN_SECONDS", 60.0
        ):
            cards, source = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source, "fallback_timeout")
        self.assertEqual(len(cards), pipeline.CARDS_PER_WEEK)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_generation_timeout_total"), 1)
        self.assertEqual(counters.get("dynamic_content_fallback_timeout_total"), 1)

    async def test_invalid_json_falls_back(self) -> None:
        async def _invalid_payload(**kwargs):  # noqa: ANN003
            return _FakeResponse("not-json")

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_invalid_payload)  # noqa: ARG005
        )
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ):
            cards, source = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source, "fallback_parse_error")
        self.assertEqual(len(cards), pipeline.CARDS_PER_WEEK)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_parse_error_total"), 1)

    async def test_retry_then_success(self) -> None:
        calls = {"count": 0}
        valid_payload = (
            '[{"title":"A","description":"B","question":"Q1"},'
            '{"title":"C","description":"D","question":"Q2"}]'
        )

        async def _flaky(**kwargs):  # noqa: ANN003
            calls["count"] += 1
            if calls["count"] == 1:
                raise RuntimeError("transient")
            return _FakeResponse(valid_payload)

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_flaky)  # noqa: ARG005
        )
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 1
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_BACKOFF_BASE_SECONDS", 0.0
        ):
            cards, source = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source, "ai")
        self.assertEqual(len(cards), 2)
        self.assertGreaterEqual(calls["count"], 2)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_generation_error_total"), 1)
        self.assertEqual(counters.get("dynamic_content_generation_success_total"), 1)

    async def test_cooldown_active_skips_provider_call(self) -> None:
        called = {"value": False}

        async def _should_not_run(**kwargs):  # noqa: ANN003
            called["value"] = True
            return _FakeResponse("[]")

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_should_not_run)  # noqa: ARG005
        )

        pipeline._activate_cooldown(30)
        with patch.dict(sys.modules, {"openai": fake_openai}):
            cards, source = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source, "fallback_cooldown_active")
        self.assertFalse(called["value"])
        self.assertEqual(len(cards), pipeline.CARDS_PER_WEEK)

    async def test_degraded_mode_activates_after_high_fallback_ratio(self) -> None:
        calls = {"count": 0}

        async def _always_timeout(**kwargs):  # noqa: ANN003
            calls["count"] += 1
            raise asyncio.TimeoutError()

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_always_timeout)  # noqa: ARG005
        )
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_MIN_ATTEMPTS", 1
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_FALLBACK_RATIO_THRESHOLD", 0.0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_DURATION_SECONDS", 30.0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_FAILURE_COOLDOWN_SECONDS", 0.0
        ):
            first_cards, first_source = await pipeline._generate_trending_cards_via_ai()
            second_cards, second_source = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(first_source, "fallback_timeout")
        self.assertEqual(second_source, "fallback_degraded_mode")
        self.assertEqual(len(first_cards), pipeline.CARDS_PER_WEEK)
        self.assertEqual(len(second_cards), pipeline.CARDS_PER_WEEK)
        # second run should short-circuit before provider call
        self.assertEqual(calls["count"], 1)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertGreaterEqual(counters.get("dynamic_content_degraded_mode_activated_total", 0), 1)
        self.assertGreaterEqual(counters.get("dynamic_content_fallback_degraded_mode_total", 0), 1)

    async def test_weekly_injection_inserts_cards(self) -> None:
        valid_payload = (
            '[{"title":"T1","description":"D1","question":"Q1"},'
            '{"title":"T2","description":"D2","question":"Q2"},'
            '{"title":"T3","description":"D3","question":"Q3"}]'
        )

        async def _ok(**kwargs):  # noqa: ANN003
            return _FakeResponse(valid_payload)

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_ok)  # noqa: ARG005
        )
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)

        with patch.dict(sys.modules, {"openai": fake_openai}):
            with patch.object(pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0):
                with Session(engine) as session:
                    inserted = await pipeline.run_weekly_injection(session)
                    session.commit()

            with Session(engine) as session:
                deck = session.exec(select(CardDeck).where(CardDeck.name == pipeline.TRENDING_DECK_NAME)).first()
                self.assertIsNotNone(deck)
                cards = session.exec(select(Card)).all()

        self.assertEqual(inserted, 3)
        self.assertEqual(len(cards), 3)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_generation_success_total"), 1)
        self.assertEqual(counters.get("dynamic_content_cards_inserted_total"), 3)

    async def test_weekly_injection_shadow_mode_skips_insert(self) -> None:
        valid_payload = '[{"title":"S1","description":"D1","question":"Q1"}]'

        async def _ok(**kwargs):  # noqa: ANN003
            return _FakeResponse(valid_payload)

        fake_openai = types.SimpleNamespace(
            AsyncOpenAI=lambda api_key=None: _FakeAsyncOpenAI(_ok)  # noqa: ARG005
        )
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.addCleanup(engine.dispose)
        SQLModel.metadata.create_all(engine)

        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_SHADOW_MODE", True
        ):
            with Session(engine) as session:
                inserted = await pipeline.run_weekly_injection(session)
                session.commit()

            with Session(engine) as session:
                cards = session.exec(select(Card)).all()

        self.assertEqual(inserted, 0)
        self.assertEqual(len(cards), 0)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_shadow_run_total"), 1)

    async def test_runtime_state_reports_cooldown_remaining(self) -> None:
        pipeline._activate_cooldown(2)
        state = pipeline.get_dynamic_content_runtime_state()
        self.assertTrue(state.get("cooldown_active"))
        self.assertGreaterEqual(int(state.get("cooldown_remaining_seconds") or 0), 1)
        self.assertIn("degraded_mode_active", state)
        self.assertIn("degraded_mode_remaining_seconds", state)
        self.assertIn("degraded_mode_store_degraded", state)
        self.assertIn("degraded_mode_fallback_ratio", state)
        self.assertIn("provider_client_initialized", state)
        self.assertIn("provider_init_retry_remaining_seconds", state)

    async def test_degraded_mode_reads_from_shared_store_when_local_state_is_empty(self) -> None:
        fake_store = _FakeCooldownStore()
        with patch.object(pipeline, "_COOLDOWN_STORE", fake_store):
            pipeline._reset_cooldown_for_test()
            pipeline._activate_degraded_mode(reason="test", fallback_ratio=1.0)
            self.assertIsInstance(fake_store.payload, dict)
            with pipeline._COOLDOWN_LOCK:
                pipeline._DEGRADED_MODE_UNTIL_TS = 0.0
            self.assertTrue(pipeline._is_degraded_mode_active())

    async def test_openai_client_singleton_is_reused_between_runs(self) -> None:
        init_calls = {"count": 0}
        valid_payload = '[{"title":"S1","description":"D1","question":"Q1"}]'

        async def _ok(**kwargs):  # noqa: ANN003
            return _FakeResponse(valid_payload)

        def _build_client(api_key=None):  # noqa: ARG001
            init_calls["count"] += 1
            return _FakeAsyncOpenAI(_ok)

        fake_openai = types.SimpleNamespace(AsyncOpenAI=_build_client)
        with patch.dict(sys.modules, {"openai": fake_openai}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ):
            cards_1, source_1 = await pipeline._generate_trending_cards_via_ai()
            cards_2, source_2 = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source_1, "ai")
        self.assertEqual(source_2, "ai")
        self.assertEqual(len(cards_1), 1)
        self.assertEqual(len(cards_2), 1)
        self.assertEqual(init_calls["count"], 1)

    async def test_provider_init_retry_window_skips_repeated_init_attempts(self) -> None:
        with patch.dict(sys.modules, {"openai": None}), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_PROVIDER_INIT_RETRY_SECONDS", 60.0
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_AI_MAX_RETRIES", 0
        ):
            cards_1, source_1 = await pipeline._generate_trending_cards_via_ai()
            cards_2, source_2 = await pipeline._generate_trending_cards_via_ai()

        self.assertEqual(source_1, "fallback_provider_unavailable")
        self.assertEqual(source_2, "fallback_provider_unavailable")
        self.assertEqual(len(cards_1), pipeline.CARDS_PER_WEEK)
        self.assertEqual(len(cards_2), pipeline.CARDS_PER_WEEK)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_provider_init_error_total"), 1)
        self.assertGreaterEqual(
            counters.get("dynamic_content_provider_init_skipped_retry_window_total", 0),
            1,
        )

    async def test_degraded_mode_hysteresis_extends_when_recovery_conditions_not_met(self) -> None:
        with pipeline._COOLDOWN_LOCK:
            pipeline._DEGRADED_MODE_UNTIL_TS = 1.0

        fake_counters = {
            "dynamic_content_generation_attempt_total": 10,
            "dynamic_content_fallback_timeout_total": 9,
        }
        with patch.object(dynamic_content_runtime_metrics, "snapshot", return_value=fake_counters), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_RECOVERY_MIN_ATTEMPTS", 1
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_RECOVERY_FALLBACK_RATIO_THRESHOLD", 0.1
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_EXTENSION_SECONDS", 30.0
        ):
            self.assertTrue(pipeline._is_degraded_mode_active())

        self.assertGreaterEqual(pipeline._degraded_mode_remaining_seconds(), 1)
        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertGreaterEqual(counters.get("dynamic_content_degraded_mode_extended_total", 0), 1)

    async def test_degraded_mode_recovers_after_expiry_when_ratio_is_healthy(self) -> None:
        with pipeline._COOLDOWN_LOCK:
            pipeline._DEGRADED_MODE_UNTIL_TS = 1.0

        fake_counters = {
            "dynamic_content_generation_attempt_total": 10,
            "dynamic_content_fallback_timeout_total": 1,
        }
        with patch.object(dynamic_content_runtime_metrics, "snapshot", return_value=fake_counters), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_RECOVERY_MIN_ATTEMPTS", 1
        ), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_DEGRADED_RECOVERY_FALLBACK_RATIO_THRESHOLD", 0.2
        ):
            self.assertFalse(pipeline._is_degraded_mode_active())

        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertGreaterEqual(counters.get("dynamic_content_degraded_mode_recovered_total", 0), 1)

    async def test_cooldown_state_can_be_loaded_from_shared_store(self) -> None:
        fake_store = _FakeCooldownStore()
        with patch.object(pipeline, "_COOLDOWN_STORE", fake_store), patch.object(
            pipeline,
            "_COOLDOWN_STORE_DEGRADED",
            False,
        ):
            pipeline._reset_cooldown_for_test()
            pipeline._activate_cooldown(30)
            # Simulate a different worker process: clear local runtime cache but keep shared store payload.
            with pipeline._COOLDOWN_LOCK:
                pipeline._COOLDOWN_UNTIL_TS = 0.0
            self.assertTrue(pipeline._is_cooldown_active())
            self.assertGreaterEqual(pipeline._cooldown_remaining_seconds(), 1)

    async def test_cooldown_store_read_error_and_recovery_metrics_are_recorded(self) -> None:
        class _FlakyStore(_FakeCooldownStore):
            def __init__(self) -> None:
                super().__init__()
                self.fail_once = True

            def load(self, key: str):
                if self.fail_once:
                    self.fail_once = False
                    raise RuntimeError("store-down")
                return {"until_ts": time() + 30}

        from time import time

        flaky_store = _FlakyStore()
        with patch.object(pipeline, "_COOLDOWN_STORE", flaky_store), patch.object(
            pipeline.settings, "DYNAMIC_CONTENT_COOLDOWN_STORE_RETRY_SECONDS", 0
        ):
            pipeline._reset_cooldown_for_test()
            self.assertFalse(pipeline._is_cooldown_active())
            with patch.object(pipeline, "_COOLDOWN_STORE_RETRY_AT_TS", 0.0):
                self.assertTrue(pipeline._is_cooldown_active())

        counters = dynamic_content_runtime_metrics.snapshot()
        self.assertEqual(counters.get("dynamic_content_cooldown_store_read_error_total"), 1)
        self.assertEqual(
            counters.get("dynamic_content_cooldown_store_read_error_runtime_error_total"),
            1,
        )
        self.assertGreaterEqual(counters.get("dynamic_content_cooldown_store_recovered_total", 0), 1)


if __name__ == "__main__":
    unittest.main()
