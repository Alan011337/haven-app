import sys
import unittest
from pathlib import Path
from uuid import uuid4
from unittest.mock import patch

from fastapi import HTTPException

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.rate_limit import _log_rate_limit_block, _raise_rate_limited  # noqa: E402
from app.services.rate_limit_runtime_metrics import RateLimitRuntimeMetrics  # noqa: E402


class RateLimitRuntimeMetricsTests(unittest.TestCase):
    def test_record_attempt_and_snapshot(self) -> None:
        metrics = RateLimitRuntimeMetrics()
        metrics.record_attempt(scope="ip", action="journal_create", endpoint="/api/journals/")
        metrics.record_attempt(scope="IP", action="journal_create", endpoint="/api/journals/")
        metrics.record_attempt(scope="device", action="card_response_create", endpoint="/api/cards/respond")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["attempt_total"], 3)
        self.assertEqual(snapshot["attempt_by_scope"]["ip"], 2)
        self.assertEqual(snapshot["attempt_by_scope"]["device"], 1)
        self.assertEqual(snapshot["attempt_by_action"]["journal_create"], 2)
        self.assertEqual(snapshot["attempt_by_action"]["card_response_create"], 1)
        self.assertEqual(snapshot["attempt_by_endpoint"]["api_journals"], 2)
        self.assertEqual(snapshot["attempt_by_endpoint"]["api_cards_respond"], 1)
        self.assertEqual(snapshot["attempt_by_action_scope"]["journal_create__ip"], 2)
        self.assertEqual(snapshot["block_rate_overall"], 0.0)

    def test_record_blocked_and_snapshot(self) -> None:
        metrics = RateLimitRuntimeMetrics()
        metrics.record_attempt(scope="ip", action="journal_create", endpoint="/api/journals/")
        metrics.record_attempt(scope="IP", action="journal_create", endpoint="/api/journals/")
        metrics.record_attempt(scope="device", action="card_response_create", endpoint="/api/cards/respond")
        metrics.record_blocked(scope="ip", action="journal_create", endpoint="/api/journals/")
        metrics.record_blocked(scope="IP", action="journal_create", endpoint="/api/journals/")
        metrics.record_blocked(scope="device", action="card_response_create", endpoint="/api/cards/respond")

        snapshot = metrics.snapshot()
        self.assertEqual(snapshot["blocked_total"], 3)
        self.assertEqual(snapshot["blocked_by_scope"]["ip"], 2)
        self.assertEqual(snapshot["blocked_by_scope"]["device"], 1)
        self.assertEqual(snapshot["blocked_by_action"]["journal_create"], 2)
        self.assertEqual(snapshot["blocked_by_action"]["card_response_create"], 1)
        self.assertEqual(snapshot["blocked_by_endpoint"]["api_journals"], 2)
        self.assertEqual(snapshot["blocked_by_endpoint"]["api_cards_respond"], 1)
        self.assertEqual(snapshot["blocked_by_action_scope"]["journal_create__ip"], 2)
        self.assertEqual(snapshot["block_rate_overall"], 1.0)
        self.assertEqual(snapshot["block_rate_by_scope"]["ip"], 1.0)
        self.assertEqual(snapshot["block_rate_by_scope"]["device"], 1.0)

    def test_invalid_amount_is_ignored(self) -> None:
        metrics = RateLimitRuntimeMetrics()
        metrics.record_blocked(scope="ip", action="journal_create", endpoint="/api/journals/", amount=0)
        metrics.record_blocked(scope="ip", action="journal_create", endpoint="/api/journals/", amount=-2)
        self.assertEqual(metrics.snapshot()["blocked_total"], 0)

    def test_log_rate_limit_block_emits_structured_warning(self) -> None:
        with patch("app.services.rate_limit.logger.warning") as mock_warning:
            _log_rate_limit_block(
                endpoint="/api/journals/",
                action="journal_create",
                scope="ip",
                user_id=uuid4(),
                partner_id=uuid4(),
                retry_after_seconds=12,
                limit_count=1,
                window_seconds=60,
            )
        self.assertEqual(mock_warning.call_count, 1)
        args = mock_warning.call_args.args
        self.assertIn("rate_limit_block", args[0])
        self.assertEqual(args[1], "/api/journals/")
        self.assertEqual(args[2], "journal_create")
        self.assertEqual(args[3], "ip")
        self.assertEqual(args[6], 12)
        self.assertEqual(args[7], 1)
        self.assertEqual(args[8], 60)

    def test_raise_rate_limited_includes_scope_headers(self) -> None:
        with self.assertRaises(HTTPException) as ctx:
            _raise_rate_limited(
                "too many",
                retry_after_seconds=9,
                scope="partner_pair",
                action="card_response_create",
                endpoint="/api/card-decks/respond/{session_id}",
                user_id=uuid4(),
                partner_id=uuid4(),
                limit_count=1,
                window_seconds=60,
            )

        exc = ctx.exception
        self.assertEqual(exc.status_code, 429)
        self.assertEqual(exc.headers.get("Retry-After"), "9")
        self.assertEqual(exc.headers.get("X-RateLimit-Scope"), "partner_pair")
        self.assertEqual(exc.headers.get("X-RateLimit-Action"), "card_response_create")


if __name__ == "__main__":
    unittest.main()
