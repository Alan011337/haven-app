"""Lightweight fuzz tests for JournalAnalysis schema contract (P0-I)."""

import random
import string
import unittest

from pydantic import ValidationError

from app.schemas.ai import CardRecommendation, JournalAnalysis


def _rand_text(min_len: int = 1, max_len: int = 80) -> str:
    length = random.randint(min_len, max_len)
    alphabet = string.ascii_letters + string.digits + " \u4e2d\u6587"
    return "".join(random.choice(alphabet) for _ in range(length)).strip() or "x"


class JournalAnalysisSchemaFuzzTests(unittest.TestCase):
    REQUIRED_FIELDS = (
        "mood_label",
        "emotional_needs",
        "advice_for_user",
        "action_for_user",
        "advice_for_partner",
        "action_for_partner",
        "card_recommendation",
        "safety_tier",
    )

    def _valid_payload(self) -> dict:
        return {
            "mood_label": _rand_text(),
            "emotional_needs": _rand_text(4, 120),
            "advice_for_user": _rand_text(4, 120),
            "action_for_user": _rand_text(2, 80),
            "advice_for_partner": _rand_text(4, 120),
            "action_for_partner": _rand_text(2, 80),
            "card_recommendation": random.choice(list(CardRecommendation)).value,
            "safety_tier": random.randint(0, 3),
        }

    def test_fuzz_valid_payloads_parse(self) -> None:
        random.seed(20260219)
        for _ in range(80):
            payload = self._valid_payload()
            parsed = JournalAnalysis.model_validate(payload)
            self.assertIn(parsed.safety_tier, (0, 1, 2, 3))

    def test_fuzz_invalid_safety_tier_rejected(self) -> None:
        random.seed(20260219)
        for _ in range(60):
            payload = self._valid_payload()
            candidate = random.randint(-10, 20)
            if candidate in (0, 1, 2, 3):
                candidate = 9
            payload["safety_tier"] = candidate
            with self.assertRaises(ValidationError):
                JournalAnalysis.model_validate(payload)

    def test_fuzz_invalid_card_recommendation_rejected(self) -> None:
        random.seed(20260219)
        for _ in range(40):
            payload = self._valid_payload()
            payload["card_recommendation"] = f"INVALID_{_rand_text(2, 8)}"
            with self.assertRaises(ValidationError):
                JournalAnalysis.model_validate(payload)

    def test_fuzz_missing_required_field_rejected(self) -> None:
        random.seed(20260219)
        for _ in range(40):
            payload = self._valid_payload()
            missing = random.choice(self.REQUIRED_FIELDS)
            payload.pop(missing, None)
            with self.assertRaises(ValidationError):
                JournalAnalysis.model_validate(payload)
