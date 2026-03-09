import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services import posthog_events  # noqa: E402


class PosthogEventsSanitizationTests(unittest.TestCase):
    def test_sanitize_properties_drops_pii_keys(self) -> None:
        payload = {
            "email": "owner@example.com",
            "token": "abc",
            "event_name": "ok",
            "request_id": "req-123",
            "content": "secret text",
        }
        sanitized = posthog_events._sanitize_properties(payload)  # noqa: SLF001
        self.assertNotIn("email", sanitized)
        self.assertNotIn("token", sanitized)
        self.assertNotIn("content", sanitized)
        self.assertEqual(sanitized["event_name"], "ok")
        self.assertEqual(sanitized["request_id"], "req-123")

    def test_sanitize_properties_truncates_long_strings(self) -> None:
        payload = {"reason": "x" * 400}
        sanitized = posthog_events._sanitize_properties(payload)  # noqa: SLF001
        self.assertEqual(len(sanitized["reason"]), 200)

    def test_send_posthog_with_retry_retries_transient_errors(self) -> None:
        send_mock = Mock(side_effect=[URLError("temporary"), None])
        with patch.object(posthog_events, "_send_posthog", send_mock):
            with patch.object(posthog_events, "_retry_attempts", return_value=2):
                with patch.object(posthog_events, "_retry_base_seconds", return_value=0.01):
                    with patch("time.sleep", return_value=None):
                        posthog_events._send_posthog_with_retry({"event": "x"})  # noqa: SLF001
        self.assertEqual(send_mock.call_count, 2)

    def test_capture_posthog_event_drops_when_queue_full(self) -> None:
        with patch.object(posthog_events.settings, "POSTHOG_ENABLED", True):
            with patch.object(posthog_events.settings, "POSTHOG_API_KEY", "test_key"):
                with patch.object(posthog_events.settings, "POSTHOG_HOST", "https://us.i.posthog.com"):
                    with patch.object(posthog_events, "_try_acquire_inflight_slot", return_value=False):
                        with patch.object(posthog_events, "_ensure_executor") as ensure_executor:
                            posthog_events.capture_posthog_event(
                                event_name="sample_event",
                                distinct_id="u-1",
                                properties={"ok": True},
                            )
                            ensure_executor.assert_not_called()


if __name__ == "__main__":
    unittest.main()
