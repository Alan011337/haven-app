import sys
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.schemas.ai import CardRecommendation, JournalAnalysis  # noqa: E402
from app.services.ai_persona import (  # noqa: E402
    apply_persona_output_guardrails,
    build_analysis_messages,
    build_dynamic_context_injection,
    infer_relationship_weather,
    resolve_relationship_weather,
)


class AIPersonaTests(unittest.TestCase):
    @staticmethod
    def _build_analysis(
        *,
        advice_for_user: str = "先深呼吸，整理當下情緒。",
        advice_for_partner: str = "先傾聽再回應，避免急著給答案。",
        action_for_partner: str = "今晚先用一句肯定開場。",
    ) -> JournalAnalysis:
        return JournalAnalysis(
            mood_label="🌿 平靜",
            emotional_needs="需要被理解與被接住。",
            advice_for_user=advice_for_user,
            action_for_user="寫下三句你此刻最真實的感受。",
            advice_for_partner=advice_for_partner,
            action_for_partner=action_for_partner,
            card_recommendation=CardRecommendation.SAFE_ZONE,
            safety_tier=0,
        )

    def test_infer_relationship_weather_conflict(self) -> None:
        weather = infer_relationship_weather("我們昨天吵架，我很生氣也很受傷。")
        self.assertEqual(weather, "conflict")

    def test_infer_relationship_weather_repair(self) -> None:
        weather = infer_relationship_weather("我今天很感謝他，真的很開心。")
        self.assertEqual(weather, "repair")

    def test_build_dynamic_context_injection_returns_empty_for_neutral(self) -> None:
        context = build_dynamic_context_injection("今天天氣普通。")
        self.assertEqual(context, "")

    def test_build_dynamic_context_injection_contains_persona_marker(self) -> None:
        context = build_dynamic_context_injection("最近冷戰又吵架，我很崩潰。")
        self.assertIn("persona_id: third_party_observer_v1", context)
        self.assertIn("relationship_weather: conflict", context)

    def test_resolve_relationship_weather_prefers_recent_hint_when_current_is_neutral(self) -> None:
        weather = resolve_relationship_weather(
            content="今天天氣普通，沒有太多情緒詞。",
            relationship_weather_hint="conflict",
        )
        self.assertEqual(weather, "conflict")

    def test_build_dynamic_context_injection_uses_hint_for_neutral_content(self) -> None:
        context = build_dynamic_context_injection(
            "今天就這樣，沒什麼特別。",
            relationship_weather_hint="repair",
        )
        self.assertIn("relationship_weather: repair", context)

    def test_build_dynamic_context_injection_ignores_invalid_hint(self) -> None:
        context = build_dynamic_context_injection(
            "今天就這樣，沒什麼特別。",
            relationship_weather_hint="unknown-signal",
        )
        self.assertEqual(context, "")

    def test_build_analysis_messages_without_dynamic_context(self) -> None:
        with patch.object(settings, "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED", False):
            messages = build_analysis_messages(
                content="我們今天有點小摩擦。",
                base_prompt="SYSTEM_PROMPT",
            )
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[0]["content"], "SYSTEM_PROMPT")
        self.assertEqual(messages[1]["role"], "user")

    def test_build_analysis_messages_with_dynamic_context(self) -> None:
        with patch.object(settings, "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED", True):
            messages = build_analysis_messages(
                content="我們昨天吵架，他覺得被忽略。",
                base_prompt="SYSTEM_PROMPT",
            )
        self.assertEqual(len(messages), 3)
        self.assertEqual(messages[1]["role"], "system")
        self.assertIn("relationship_weather: conflict", messages[1]["content"])

    def test_build_analysis_messages_with_hint_context(self) -> None:
        with patch.object(settings, "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED", True):
            messages = build_analysis_messages(
                content="今天過得很平淡。",
                base_prompt="SYSTEM_PROMPT",
                relationship_weather_hint="conflict",
            )
        self.assertEqual(len(messages), 3)
        self.assertIn("relationship_weather: conflict", messages[1]["content"])

    def test_apply_persona_output_guardrails_noop_when_no_violation(self) -> None:
        analysis = self._build_analysis()
        sanitized, meta = apply_persona_output_guardrails(analysis)
        self.assertFalse(meta["adjusted"])
        self.assertEqual(meta["rule_ids"], [])
        self.assertEqual(meta["fields"], [])
        self.assertEqual(sanitized.advice_for_partner, analysis.advice_for_partner)

    def test_apply_persona_output_guardrails_rewrites_partner_identity_claim(self) -> None:
        analysis = self._build_analysis(
            advice_for_partner="我是你的男朋友，我會一直在你身邊。",
        )
        sanitized, meta = apply_persona_output_guardrails(analysis)
        self.assertTrue(meta["adjusted"])
        self.assertIn("partner_identity_claim_zh", meta["rule_ids"])
        self.assertIn("advice_for_partner", meta["fields"])
        self.assertNotIn("我是你的男朋友", sanitized.advice_for_partner)
        self.assertIn("中立第三者觀察者", sanitized.advice_for_partner)

    def test_apply_persona_output_guardrails_rewrites_direct_love_phrase(self) -> None:
        analysis = self._build_analysis(
            action_for_partner="我愛你，今晚我們好好聊聊。",
        )
        sanitized, meta = apply_persona_output_guardrails(analysis)
        self.assertTrue(meta["adjusted"])
        self.assertIn("direct_love_phrase_zh", meta["rule_ids"])
        self.assertIn("action_for_partner", meta["fields"])
        self.assertNotIn("我愛你", sanitized.action_for_partner)
        self.assertIn("看起來你的伴侶很在乎你", sanitized.action_for_partner)


if __name__ == "__main__":
    unittest.main()
