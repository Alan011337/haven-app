import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.services import rate_limit as rate_limit_module


class _AlwaysBlockedLimiter:
    def allow_and_record(
        self,
        *,
        key: str,
        limit_count: int,
        window_seconds: int,
    ) -> tuple[bool, int]:
        return False, 7


class LoginRateLimitLogRedactionTests(unittest.TestCase):
    def test_login_rate_limit_log_redacts_client_ip(self) -> None:
        with patch.object(rate_limit_module, "_login_ip_scope_limiter", _AlwaysBlockedLimiter()):
            with self.assertLogs(rate_limit_module.logger, level="WARNING") as captured:
                with self.assertRaises(HTTPException) as raised:
                    rate_limit_module.enforce_login_rate_limit(
                        client_ip="203.0.113.42",
                        ip_limit_count=1,
                        ip_window_seconds=60,
                    )

        self.assertEqual(raised.exception.status_code, 429)
        merged = "\n".join(captured.output)
        self.assertIn("Login rate-limited IP=", merged)
        self.assertIn("203.0.x.x", merged)
        self.assertNotIn("203.0.113.42", merged)


if __name__ == "__main__":
    unittest.main()
