# Prompt Supply Chain Tests (AI-SUPPLY-01)
#
# Validates that the system prompt integrity mechanisms are working:
# - Hash matches the expected value computed at import time
# - Version string follows the expected format
# - verify_prompt_integrity() passes under normal conditions
# - Tampering is detected

import hashlib
import re
import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.prompts import (  # noqa: E402
    CURRENT_PROMPT_VERSION,
    HAVEN_SYSTEM_PROMPT,
    PROMPT_POLICY_HASH,
    verify_prompt_integrity,
)


class PromptHashTests(unittest.TestCase):
    """Ensure PROMPT_POLICY_HASH correctly represents the prompt content."""

    def test_hash_matches_prompt_content(self) -> None:
        """Recompute SHA-256 independently and compare."""
        expected = hashlib.sha256(HAVEN_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        self.assertEqual(
            PROMPT_POLICY_HASH,
            expected,
            "PROMPT_POLICY_HASH does not match a fresh SHA-256 of HAVEN_SYSTEM_PROMPT.",
        )

    def test_hash_is_valid_sha256_hex(self) -> None:
        self.assertEqual(len(PROMPT_POLICY_HASH), 64)
        self.assertRegex(PROMPT_POLICY_HASH, r"^[0-9a-f]{64}$")

    def test_hash_is_deterministic(self) -> None:
        """Calling the hash twice must produce the same result."""
        h1 = hashlib.sha256(HAVEN_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        h2 = hashlib.sha256(HAVEN_SYSTEM_PROMPT.encode("utf-8")).hexdigest()
        self.assertEqual(h1, h2)


class PromptIntegrityTests(unittest.TestCase):
    """Test the verify_prompt_integrity() function."""

    def test_integrity_passes(self) -> None:
        self.assertTrue(
            verify_prompt_integrity(),
            "verify_prompt_integrity() should return True for an untampered prompt.",
        )

    def test_integrity_detects_tampering(self) -> None:
        """Simulate tampering by monkey-patching the hash, then restore it."""
        import app.core.prompts as prompts_module

        original_hash = prompts_module.PROMPT_POLICY_HASH
        try:
            prompts_module.PROMPT_POLICY_HASH = "0" * 64  # fake hash
            self.assertFalse(
                prompts_module.verify_prompt_integrity(),
                "verify_prompt_integrity() should return False after hash tampering.",
            )
        finally:
            prompts_module.PROMPT_POLICY_HASH = original_hash

    def test_integrity_detects_prompt_mutation(self) -> None:
        """Simulate prompt mutation by monkey-patching the prompt, then restore."""
        import app.core.prompts as prompts_module

        original_prompt = prompts_module.HAVEN_SYSTEM_PROMPT
        try:
            prompts_module.HAVEN_SYSTEM_PROMPT = "TAMPERED PROMPT CONTENT"
            self.assertFalse(
                prompts_module.verify_prompt_integrity(),
                "verify_prompt_integrity() should detect prompt content mutation.",
            )
        finally:
            prompts_module.HAVEN_SYSTEM_PROMPT = original_prompt


class PromptVersionTests(unittest.TestCase):
    """Verify version string format and consistency."""

    VERSION_PATTERN = re.compile(
        r"^\d{4}-\d{2}-\d{2}_v\d+_[a-z][a-z0-9_]*$"
    )

    def test_version_follows_expected_format(self) -> None:
        self.assertRegex(
            CURRENT_PROMPT_VERSION,
            self.VERSION_PATTERN,
            f"Version '{CURRENT_PROMPT_VERSION}' does not match YYYY-MM-DD_vN_descriptor.",
        )

    def test_version_is_non_empty(self) -> None:
        self.assertTrue(len(CURRENT_PROMPT_VERSION) > 0)

    def test_version_contains_date_segment(self) -> None:
        date_part = CURRENT_PROMPT_VERSION.split("_")[0]
        self.assertRegex(date_part, r"^\d{4}-\d{2}-\d{2}$")

    def test_version_contains_version_number(self) -> None:
        parts = CURRENT_PROMPT_VERSION.split("_")
        self.assertTrue(
            any(p.startswith("v") and p[1:].isdigit() for p in parts),
            "Version string must contain a 'vN' segment.",
        )


class PromptContentSanityTests(unittest.TestCase):
    """Basic sanity checks on prompt content."""

    def test_prompt_is_non_empty(self) -> None:
        self.assertGreater(len(HAVEN_SYSTEM_PROMPT.strip()), 100)

    def test_prompt_contains_haven_identity(self) -> None:
        self.assertIn("Haven", HAVEN_SYSTEM_PROMPT)

    def test_prompt_contains_json_schema_instruction(self) -> None:
        self.assertIn("JSON Schema", HAVEN_SYSTEM_PROMPT)


if __name__ == "__main__":
    unittest.main()
