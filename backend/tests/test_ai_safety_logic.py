import sys
import unittest
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_safety import (  # noqa: E402
    ModerationSignal,
    derive_safety_tier_from_moderation,
    merge_safety_tier,
    normalize_category_bools,
    normalize_category_key,
    normalize_category_scores,
    to_dict,
)


class _CategoryPayload:
    def __init__(self):
        self.self_harm = True
        self.some_score = "0.2"


class _ModelDumpPayload:
    def model_dump(self):
        return {"self-harm/instructions": 0.91, "violence": 0.15}


class _GetterRaisesPayload:
    ok = 1

    @property
    def broken(self):
        raise RuntimeError("broken attr")


class AiSafetyLogicTests(unittest.TestCase):
    def test_normalize_category_key(self) -> None:
        self.assertEqual(
            normalize_category_key("self-harm/instructions"),
            "self_harm_instructions",
        )

    def test_to_dict_handles_model_dump(self) -> None:
        payload = _ModelDumpPayload()
        as_dict = to_dict(payload)
        self.assertEqual(as_dict["self-harm/instructions"], 0.91)

    def test_to_dict_ignores_broken_attributes(self) -> None:
        payload = _GetterRaisesPayload()
        as_dict = to_dict(payload)
        self.assertEqual(as_dict["ok"], 1)
        self.assertNotIn("broken", as_dict)

    def test_normalize_category_bools_from_object(self) -> None:
        normalized = normalize_category_bools(_CategoryPayload())
        self.assertEqual(normalized["self_harm"], True)
        self.assertEqual(normalized["some_score"], True)

    def test_normalize_category_scores_from_mixed_values(self) -> None:
        normalized = normalize_category_scores(
            {"self-harm/intent": "0.66", "invalid": "x", "violence": 0.1}
        )
        self.assertAlmostEqual(normalized["self_harm_intent"], 0.66)
        self.assertAlmostEqual(normalized["violence"], 0.1)
        self.assertNotIn("invalid", normalized)

    def test_derive_tier_three_when_severe_category_true(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={"self_harm_instructions": True},
            category_scores={},
        )
        self.assertEqual(tier, 3)

    def test_derive_tier_two_when_tier2_score_crosses_threshold(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"harassment_threatening": 0.36},
        )
        self.assertEqual(tier, 2)

    def test_derive_tier_one_when_flagged_without_high_scores(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=True,
            categories={},
            category_scores={"violence": 0.05},
        )
        self.assertEqual(tier, 1)

    def test_derive_tier_zero_when_clean(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"violence": 0.01},
        )
        self.assertEqual(tier, 0)

    def test_merge_safety_tier_prefers_higher_value(self) -> None:
        signal = ModerationSignal(
            safety_tier=2,
            flagged=True,
            categories={"violence": True},
            category_scores={"violence": 0.9},
            model="omni-moderation-latest",
        )
        self.assertEqual(merge_safety_tier(1, signal), 2)
        self.assertEqual(merge_safety_tier(3, signal), 3)
        self.assertEqual(merge_safety_tier(1, None), 1)


if __name__ == "__main__":
    unittest.main()
