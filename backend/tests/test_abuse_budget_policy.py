import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


class AbuseBudgetPolicyTests(unittest.TestCase):
    def test_rate_limit_values_are_positive(self) -> None:
        numeric_values = [
            ("JOURNAL_RATE_LIMIT_COUNT", settings.JOURNAL_RATE_LIMIT_COUNT),
            ("JOURNAL_RATE_LIMIT_WINDOW_SECONDS", settings.JOURNAL_RATE_LIMIT_WINDOW_SECONDS),
            ("JOURNAL_RATE_LIMIT_IP_COUNT", settings.JOURNAL_RATE_LIMIT_IP_COUNT),
            ("JOURNAL_RATE_LIMIT_DEVICE_COUNT", settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT),
            ("JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT", settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT),
            ("CARD_RESPONSE_RATE_LIMIT_COUNT", settings.CARD_RESPONSE_RATE_LIMIT_COUNT),
            ("CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS", settings.CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS),
            ("CARD_RESPONSE_RATE_LIMIT_IP_COUNT", settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT),
            ("CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT", settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT),
            (
                "CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT",
                settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT,
            ),
            ("PAIRING_ATTEMPT_RATE_LIMIT_COUNT", settings.PAIRING_ATTEMPT_RATE_LIMIT_COUNT),
            ("PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS", settings.PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS),
            ("PAIRING_FAILURE_COOLDOWN_THRESHOLD", settings.PAIRING_FAILURE_COOLDOWN_THRESHOLD),
            ("PAIRING_FAILURE_COOLDOWN_SECONDS", settings.PAIRING_FAILURE_COOLDOWN_SECONDS),
            ("PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT", settings.PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT),
            ("PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS", settings.PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS),
            ("PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD", settings.PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD),
            ("PAIRING_IP_FAILURE_COOLDOWN_SECONDS", settings.PAIRING_IP_FAILURE_COOLDOWN_SECONDS),
            ("WS_MAX_CONNECTIONS_PER_USER", settings.WS_MAX_CONNECTIONS_PER_USER),
            ("WS_MAX_CONNECTIONS_GLOBAL", settings.WS_MAX_CONNECTIONS_GLOBAL),
            ("WS_MESSAGE_RATE_LIMIT_COUNT", settings.WS_MESSAGE_RATE_LIMIT_COUNT),
            ("WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS", settings.WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS),
            ("WS_MESSAGE_BACKOFF_SECONDS", settings.WS_MESSAGE_BACKOFF_SECONDS),
            ("WS_MAX_PAYLOAD_BYTES", settings.WS_MAX_PAYLOAD_BYTES),
        ]

        for name, value in numeric_values:
            with self.subTest(name=name):
                self.assertGreater(value, 0, f"{name} must be > 0")

    def test_pairing_ip_budget_is_not_weaker_than_user_budget(self) -> None:
        self.assertGreaterEqual(
            settings.PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT,
            settings.PAIRING_ATTEMPT_RATE_LIMIT_COUNT,
        )
        self.assertGreaterEqual(
            settings.PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD,
            settings.PAIRING_FAILURE_COOLDOWN_THRESHOLD,
        )
        self.assertGreaterEqual(
            settings.PAIRING_IP_FAILURE_COOLDOWN_SECONDS,
            settings.PAIRING_FAILURE_COOLDOWN_SECONDS,
        )

    def test_websocket_envelope_bounds(self) -> None:
        self.assertGreaterEqual(
            settings.WS_MAX_CONNECTIONS_GLOBAL,
            settings.WS_MAX_CONNECTIONS_PER_USER,
        )
        self.assertLessEqual(settings.WS_MESSAGE_RATE_LIMIT_COUNT, 300)
        self.assertLessEqual(settings.WS_MAX_PAYLOAD_BYTES, 8192)

    def test_write_path_envelope_bounds(self) -> None:
        self.assertLessEqual(settings.JOURNAL_RATE_LIMIT_COUNT, 120)
        self.assertLessEqual(settings.CARD_RESPONSE_RATE_LIMIT_COUNT, 180)
        self.assertGreaterEqual(settings.JOURNAL_RATE_LIMIT_IP_COUNT, settings.JOURNAL_RATE_LIMIT_COUNT)
        self.assertGreaterEqual(settings.JOURNAL_RATE_LIMIT_DEVICE_COUNT, settings.JOURNAL_RATE_LIMIT_COUNT)
        self.assertGreaterEqual(
            settings.JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT,
            settings.JOURNAL_RATE_LIMIT_COUNT,
        )
        self.assertGreaterEqual(
            settings.CARD_RESPONSE_RATE_LIMIT_IP_COUNT,
            settings.CARD_RESPONSE_RATE_LIMIT_COUNT,
        )
        self.assertGreaterEqual(
            settings.CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT,
            settings.CARD_RESPONSE_RATE_LIMIT_COUNT,
        )
        self.assertGreaterEqual(
            settings.CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT,
            settings.CARD_RESPONSE_RATE_LIMIT_COUNT,
        )


if __name__ == "__main__":
    unittest.main()
