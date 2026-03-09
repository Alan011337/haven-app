import sys
import unittest
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402


class PushAbuseBudgetPolicyTests(unittest.TestCase):
    def test_push_budget_values_are_positive(self) -> None:
        numeric_values = [
            ("PUSH_MAX_SUBSCRIPTIONS_PER_USER", settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER),
            ("PUSH_DEFAULT_TTL_SECONDS", settings.PUSH_DEFAULT_TTL_SECONDS),
            ("PUSH_DRY_RUN_SAMPLE_SIZE", settings.PUSH_DRY_RUN_SAMPLE_SIZE),
            ("PUSH_INVALID_RETENTION_DAYS", settings.PUSH_INVALID_RETENTION_DAYS),
            ("PUSH_TOMBSTONE_PURGE_DAYS", settings.PUSH_TOMBSTONE_PURGE_DAYS),
            ("PUSH_JWT_MAX_EXP_SECONDS", settings.PUSH_JWT_MAX_EXP_SECONDS),
            ("HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS", settings.HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS),
            ("HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES", settings.HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES),
        ]
        for name, value in numeric_values:
            with self.subTest(name=name):
                self.assertGreater(value, 0, f"{name} must be > 0")

    def test_push_envelope_bounds(self) -> None:
        self.assertLessEqual(settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER, 25)
        self.assertLessEqual(settings.PUSH_DRY_RUN_SAMPLE_SIZE, 20)
        self.assertLessEqual(settings.PUSH_DEFAULT_TTL_SECONDS, settings.PUSH_JWT_MAX_EXP_SECONDS)
        self.assertGreaterEqual(
            settings.PUSH_TOMBSTONE_PURGE_DAYS,
            settings.PUSH_INVALID_RETENTION_DAYS,
        )

    def test_push_slo_targets_are_reasonable(self) -> None:
        self.assertGreaterEqual(settings.HEALTH_PUSH_DELIVERY_RATE_TARGET, 0.9)
        self.assertLessEqual(settings.HEALTH_PUSH_DELIVERY_RATE_TARGET, 1.0)
        self.assertGreater(settings.HEALTH_PUSH_DISPATCH_P95_MS_TARGET, 0)
        self.assertGreater(settings.HEALTH_PUSH_DRY_RUN_P95_MS_TARGET, 0)
        self.assertGreaterEqual(settings.HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX, 0)


if __name__ == "__main__":
    unittest.main()
