# AI JSON schema contract (P0-I): JournalAnalysis compliance

"""Tests that API/AI output conforms to JournalAnalysis schema (valid sample + invalid rejected)."""

import unittest
from pydantic import ValidationError

from app.schemas.ai import JournalAnalysis, CardRecommendation


class TestJournalAnalysisSchemaContract(unittest.TestCase):
    """Contract: valid payload parses; invalid payload raises ValidationError."""

    VALID_MINIMAL = {
        "mood_label": "😊 開心",
        "emotional_needs": "渴望被看見與分享",
        "advice_for_user": "保持當下覺察",
        "action_for_user": "傳一句話給伴侶",
        "advice_for_partner": "積極回應他的快樂",
        "action_for_partner": "問他今天最開心的事",
        "card_recommendation": CardRecommendation.DAILY_VIBE.value,
        "safety_tier": 0,
    }

    def test_valid_minimal_parses(self) -> None:
        obj = JournalAnalysis.model_validate(TestJournalAnalysisSchemaContract.VALID_MINIMAL)
        self.assertEqual(obj.safety_tier, 0)
        self.assertEqual(obj.card_recommendation, CardRecommendation.DAILY_VIBE)
        self.assertIsInstance(obj.mood_label, str)

    def test_valid_with_safety_tier_2_parses(self) -> None:
        payload = {**TestJournalAnalysisSchemaContract.VALID_MINIMAL, "safety_tier": 2}
        obj = JournalAnalysis.model_validate(payload)
        self.assertEqual(obj.safety_tier, 2)

    def test_invalid_safety_tier_rejected(self) -> None:
        payload = {**TestJournalAnalysisSchemaContract.VALID_MINIMAL, "safety_tier": 4}
        with self.assertRaises(ValidationError):
            JournalAnalysis.model_validate(payload)

    def test_invalid_missing_required_rejected(self) -> None:
        payload = {"mood_label": "ok", "safety_tier": 0}
        with self.assertRaises(ValidationError):
            JournalAnalysis.model_validate(payload)

    def test_invalid_card_recommendation_rejected(self) -> None:
        payload = {**TestJournalAnalysisSchemaContract.VALID_MINIMAL, "card_recommendation": "INVALID_DECK"}
        with self.assertRaises(ValidationError):
            JournalAnalysis.model_validate(payload)
