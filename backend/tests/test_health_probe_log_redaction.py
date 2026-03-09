import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.core import health_routes as health_module  # noqa: E402


class HealthProbeLogRedactionTests(unittest.TestCase):
    def test_database_probe_log_masks_exception_details(self) -> None:
        with patch(
            "app.core.health_routes.Session",
            side_effect=RuntimeError("postgresql://svc:super-secret@db.internal:5432/haven"),
        ):
            with self.assertLogs(health_module.logger, level="WARNING") as captured:
                payload = health_module._probe_database()

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"], "RuntimeError")
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("postgresql://", merged)

    def test_redis_probe_log_masks_exception_details(self) -> None:
        original_backend = settings.ABUSE_GUARD_STORE_BACKEND
        original_redis_url = settings.ABUSE_GUARD_REDIS_URL
        settings.ABUSE_GUARD_STORE_BACKEND = "redis"
        settings.ABUSE_GUARD_REDIS_URL = "redis://:super-secret@redis.internal:6379/0"
        self.addCleanup(setattr, settings, "ABUSE_GUARD_STORE_BACKEND", original_backend)
        self.addCleanup(setattr, settings, "ABUSE_GUARD_REDIS_URL", original_redis_url)

        class _FakeRedisClient:
            def ping(self) -> None:
                raise RuntimeError("redis://:super-secret@redis.internal:6379/0 ping failed")

        fake_redis_module = SimpleNamespace(
            Redis=SimpleNamespace(from_url=lambda *_args, **_kwargs: _FakeRedisClient())
        )

        with patch.dict(sys.modules, {"redis": fake_redis_module}):
            with self.assertLogs(health_module.logger, level="WARNING") as captured:
                payload = health_module._probe_redis_if_configured()

        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"], "RuntimeError")
        merged = "\n".join(captured.output)
        self.assertIn("reason=RuntimeError", merged)
        self.assertNotIn("super-secret", merged)
        self.assertNotIn("redis://", merged)


if __name__ == "__main__":
    unittest.main()
