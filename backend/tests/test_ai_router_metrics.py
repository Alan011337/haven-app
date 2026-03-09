from __future__ import annotations

import unittest

from app.services.ai_router_metrics import sanitize_metric_key, sanitize_metric_label


class AIRouterMetricsSanitizeTests(unittest.TestCase):
    def test_sanitize_metric_key_normalizes_symbol_noise(self) -> None:
        self.assertEqual(sanitize_metric_key(" OpenAI.Premium-1 "), "openai_premium_1")

    def test_sanitize_metric_label_uses_unknown_for_out_of_allowlist(self) -> None:
        self.assertEqual(
            sanitize_metric_label(
                raw="unknown-provider",
                allowlist={"openai", "gemini", "unknown"},
            ),
            "unknown",
        )

    def test_sanitize_metric_label_accepts_known_bucket(self) -> None:
        self.assertEqual(
            sanitize_metric_label(
                raw="gemini",
                allowlist={"openai", "gemini", "unknown"},
            ),
            "gemini",
        )

    def test_sanitize_metric_label_blocks_unbounded_token_like_label(self) -> None:
        self.assertEqual(
            sanitize_metric_label(
                raw="request_id_1234",
                allowlist={"openai", "gemini", "unknown", "request_id_1234"},
            ),
            "unknown",
        )

    def test_sanitize_metric_label_blocks_auth_token_fields(self) -> None:
        self.assertEqual(
            sanitize_metric_label(
                raw="session_token",
                allowlist={"session_token", "unknown"},
            ),
            "unknown",
        )

    def test_sanitize_metric_label_blocks_secret_like_fields(self) -> None:
        self.assertEqual(
            sanitize_metric_label(
                raw="password_reset_flow",
                allowlist={"password_reset_flow", "unknown"},
            ),
            "unknown",
        )


if __name__ == "__main__":
    unittest.main()
