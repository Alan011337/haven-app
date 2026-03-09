from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.ai_router_retry import (  # noqa: E402
    compute_backoff_seconds,
    parse_retry_after_seconds,
)


class AiRouterRetryTests(unittest.TestCase):
    def test_parse_retry_after_handles_none_and_negative(self) -> None:
        self.assertIsNone(parse_retry_after_seconds(None))
        self.assertEqual(parse_retry_after_seconds(-3), 0.0)
        self.assertEqual(parse_retry_after_seconds(2.5), 2.5)

    def test_compute_backoff_supports_full_jitter(self) -> None:
        policy = SimpleNamespace(backoff_base_ms=500, backoff_max_ms=4000, backoff_jitter_mode="full")
        with patch("app.services.ai_router_retry.random.uniform", return_value=0.321) as mocked:
            delay = compute_backoff_seconds(attempt=2, policy=policy)
        self.assertEqual(delay, 0.321)
        mocked.assert_called_once()

    def test_compute_backoff_without_jitter_returns_growth(self) -> None:
        policy = SimpleNamespace(backoff_base_ms=200, backoff_max_ms=4000, backoff_jitter_mode="none")
        self.assertEqual(compute_backoff_seconds(attempt=3, policy=policy), 0.8)

    def test_compute_backoff_returns_zero_when_disabled(self) -> None:
        policy = SimpleNamespace(backoff_base_ms=0, backoff_max_ms=0, backoff_jitter_mode="none")
        self.assertEqual(compute_backoff_seconds(attempt=1, policy=policy), 0.0)


if __name__ == "__main__":
    unittest.main()
