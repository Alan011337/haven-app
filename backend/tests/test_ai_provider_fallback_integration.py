import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.ai import CardRecommendation, JournalAnalysis  # noqa: E402
from app.services import ai as ai_module  # noqa: E402
from app.services.ai_router import AIProviderAdapter, AIProviderError, AIRoute  # noqa: E402


def _healthy_analysis() -> JournalAnalysis:
    return JournalAnalysis(
        mood_label="🌿 平靜",
        emotional_needs="希望被理解",
        advice_for_user="先深呼吸",
        action_for_user="喝一杯水",
        advice_for_partner="給予陪伴",
        action_for_partner="說一句支持的話",
        card_recommendation=CardRecommendation.SAFE_ZONE,
        safety_tier=0,
    )


class AIProviderFallbackIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_analyze_journal_uses_fallback_provider_when_primary_fails(self) -> None:
        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )

        async def gemini_fail() -> tuple[JournalAnalysis, str]:
            raise AIProviderError(provider="gemini", reason="timeout", retryable=True)

        async def openai_success() -> tuple[JournalAnalysis, str]:
            return _healthy_analysis(), "gpt-4o-mini"

        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_fail),
            "openai": AIProviderAdapter(provider="openai", run=openai_success),
        }

        with patch.object(ai_module, "detect_prompt_abuse", return_value=SimpleNamespace(flagged=False, matches=[])):
            with patch.object(ai_module, "_run_moderation_precheck", AsyncMock(return_value=(None, False))):
                with patch.object(ai_module, "select_task_route", return_value=route):
                    with patch.object(ai_module, "_build_analysis_provider_adapters", return_value=adapters):
                        with self.assertLogs(ai_module.logger, level="WARNING") as captured:
                            result = await ai_module.analyze_journal("test-content")

        self.assertTrue(result["parse_success"])
        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["model_version"], "gpt-4o-mini")
        merged = "\n".join(captured.output)
        self.assertIn("AI router fallback succeeded", merged)

    async def test_analyze_journal_returns_safe_fallback_when_all_providers_fail(self) -> None:
        route = AIRoute(
            selected_provider="gemini",
            provider_chain=("gemini", "openai"),
            fallback_enabled=True,
            reason="configured_primary",
        )

        async def gemini_fail() -> tuple[JournalAnalysis, str]:
            raise AIProviderError(provider="gemini", reason="status_5xx", retryable=True)

        async def openai_fail() -> tuple[JournalAnalysis, str]:
            raise AIProviderError(provider="openai", reason="timeout", retryable=True)

        adapters = {
            "gemini": AIProviderAdapter(provider="gemini", run=gemini_fail),
            "openai": AIProviderAdapter(provider="openai", run=openai_fail),
        }

        with patch.object(ai_module, "detect_prompt_abuse", return_value=SimpleNamespace(flagged=False, matches=[])):
            with patch.object(ai_module, "_run_moderation_precheck", AsyncMock(return_value=(None, False))):
                with patch.object(ai_module, "select_task_route", return_value=route):
                    with patch.object(ai_module, "_build_analysis_provider_adapters", return_value=adapters):
                        with self.assertLogs(ai_module.logger, level="WARNING") as captured:
                            result = await ai_module.analyze_journal("test-content")

        self.assertFalse(result["parse_success"])
        self.assertIn("連線不穩定", result["advice_for_user"])
        merged = "\n".join(captured.output)
        self.assertIn("AI provider fallback exhausted", merged)


if __name__ == "__main__":
    unittest.main()
