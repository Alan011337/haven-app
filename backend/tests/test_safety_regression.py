# Safety Regression Hook (AI-EVAL-02 / EVAL-06)
#
# Aggregates safety-critical regression assertions:
# - Safety tier policy constants have not changed unexpectedly
# - Prompt version is tracked and follows expected format
# - Moderation thresholds remain within expected bounds
# - The system prompt contains the immutable policies section
#
# NOTE: security-gate.sh includes this file in the pytest invocation (line 274).

import re
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_safety import (  # noqa: E402
    TIER2_KEYS,
    TIER3_KEYS,
    derive_safety_tier_from_moderation,
)
from app.core.prompts import (  # noqa: E402
    CURRENT_PROMPT_VERSION,
    HAVEN_SYSTEM_PROMPT,
    PROMPT_POLICY_HASH,
    verify_prompt_integrity,
)


class SafetyTierConstantsRegressionTests(unittest.TestCase):
    """Ensure that safety tier key-sets have not been silently altered."""

    EXPECTED_TIER3_KEYS = {
        "self_harm_instructions",
        "violence_graphic",
        "sexual_minors",
        "illicit_violent",
    }

    EXPECTED_TIER2_KEYS = {
        "self_harm",
        "self_harm_intent",
        "violence",
        "harassment_threatening",
        "hate_threatening",
    }

    def test_tier3_keys_unchanged(self) -> None:
        self.assertEqual(
            TIER3_KEYS,
            self.EXPECTED_TIER3_KEYS,
            "TIER3_KEYS must not change without deliberate review.",
        )

    def test_tier2_keys_unchanged(self) -> None:
        self.assertEqual(
            TIER2_KEYS,
            self.EXPECTED_TIER2_KEYS,
            "TIER2_KEYS must not change without deliberate review.",
        )


class ModerationThresholdRegressionTests(unittest.TestCase):
    """Guard the numerical thresholds used inside derive_safety_tier_from_moderation.

    We test via observable behaviour rather than reading internal constants
    so this will break if the threshold logic is silently weakened.
    """

    def test_tier3_threshold_0_70_triggers(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"self_harm_instructions": 0.70},
        )
        self.assertEqual(tier, 3, "0.70 on tier3 key must still yield tier 3")

    def test_tier3_threshold_0_69_does_not_trigger_tier3(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"self_harm_instructions": 0.69},
        )
        self.assertLess(tier, 3, "0.69 on tier3 key must NOT yield tier 3")

    def test_tier2_threshold_0_35_triggers(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"self_harm": 0.35},
        )
        self.assertEqual(tier, 2, "0.35 on tier2 key must still yield tier 2")

    def test_tier2_threshold_0_34_does_not_trigger_tier2(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"self_harm": 0.34},
        )
        self.assertLess(tier, 2, "0.34 on tier2 key must NOT yield tier 2")

    def test_tier1_threshold_0_20_triggers(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"harassment": 0.20},
        )
        self.assertEqual(tier, 1, "0.20 any-score must still yield tier 1")

    def test_tier1_threshold_0_19_does_not_trigger_tier1(self) -> None:
        tier = derive_safety_tier_from_moderation(
            flagged=False,
            categories={},
            category_scores={"harassment": 0.19},
        )
        self.assertEqual(tier, 0, "0.19 any-score must remain tier 0")


class PromptVersionRegressionTests(unittest.TestCase):
    """Ensure prompt version tracking stays consistent."""

    # Expected format: YYYY-MM-DD_v<N>_<descriptor>
    VERSION_PATTERN = re.compile(
        r"^\d{4}-\d{2}-\d{2}_v\d+_[a-z][a-z0-9_]*$"
    )

    def test_prompt_version_format(self) -> None:
        self.assertRegex(
            CURRENT_PROMPT_VERSION,
            self.VERSION_PATTERN,
            f"CURRENT_PROMPT_VERSION '{CURRENT_PROMPT_VERSION}' does not match expected pattern.",
        )

    def test_prompt_version_is_not_empty(self) -> None:
        self.assertTrue(
            CURRENT_PROMPT_VERSION and len(CURRENT_PROMPT_VERSION) > 5,
            "Prompt version must be a non-trivial string.",
        )


class PromptImmutablePoliciesRegressionTests(unittest.TestCase):
    """Verify the system prompt still contains the three immutable policies."""

    def test_contains_immutable_policies_header(self) -> None:
        self.assertIn(
            "不可違反的政策 (Immutable Policies)",
            HAVEN_SYSTEM_PROMPT,
        )

    def test_contains_non_impersonation(self) -> None:
        self.assertIn("不冒充伴侶", HAVEN_SYSTEM_PROMPT)
        self.assertIn(
            "你永遠不能假裝是使用者的伴侶",
            HAVEN_SYSTEM_PROMPT,
        )

    def test_contains_coaching_boundaries(self) -> None:
        self.assertIn("關係教練邊界", HAVEN_SYSTEM_PROMPT)
        self.assertIn("你不是心理治療師或醫師", HAVEN_SYSTEM_PROMPT)

    def test_contains_crisis_consistency(self) -> None:
        self.assertIn("危機一致化", HAVEN_SYSTEM_PROMPT)
        self.assertIn("safety_tier >= 2", HAVEN_SYSTEM_PROMPT)

    def test_safety_circuit_breaker_section(self) -> None:
        self.assertIn("安全斷路器", HAVEN_SYSTEM_PROMPT)
        self.assertIn("1925", HAVEN_SYSTEM_PROMPT)
        self.assertIn("113", HAVEN_SYSTEM_PROMPT)


class PromptIntegrityRegressionTests(unittest.TestCase):
    """Verify the prompt hash and integrity check work correctly."""

    def test_prompt_policy_hash_is_sha256(self) -> None:
        self.assertEqual(len(PROMPT_POLICY_HASH), 64, "SHA-256 hash should be 64 hex chars")
        self.assertRegex(PROMPT_POLICY_HASH, r"^[0-9a-f]{64}$")

    def test_verify_prompt_integrity_passes(self) -> None:
        self.assertTrue(
            verify_prompt_integrity(),
            "Prompt integrity check must pass (hash mismatch detected).",
        )


if __name__ == "__main__":
    unittest.main()
