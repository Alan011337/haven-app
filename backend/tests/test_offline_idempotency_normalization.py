from __future__ import annotations

import unittest

from app.services.offline_idempotency import normalize_idempotency_key


class OfflineIdempotencyNormalizationTests(unittest.TestCase):
    def test_prefers_idempotency_key(self) -> None:
        value = normalize_idempotency_key(
            idempotency_key="offline-abc-1234",
            x_request_id="request-fallback-5678",
        )
        self.assertEqual(value, "offline-abc-1234")

    def test_falls_back_to_request_id(self) -> None:
        value = normalize_idempotency_key(
            idempotency_key=None,
            x_request_id="request-fallback-5678",
        )
        self.assertEqual(value, "request-fallback-5678")

    def test_rejects_too_short_key(self) -> None:
        value = normalize_idempotency_key(
            idempotency_key="short",
            x_request_id=None,
        )
        self.assertIsNone(value)


if __name__ == "__main__":
    unittest.main()

