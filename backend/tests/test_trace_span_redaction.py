import unittest

from app.middleware.request_context import (
    mode_var,
    partner_id_var,
    request_id_var,
    session_id_var,
    user_id_var,
)
from app.services.trace_span import trace_span


class TraceSpanRedactionTests(unittest.TestCase):
    def test_trace_span_masks_sensitive_fields(self) -> None:
        with self.assertLogs("app.services.trace_span", level="INFO") as captured:
            with trace_span(
                "trace-redaction",
                email="alice@example.com",
                journal_content="my private text",
                api_key="sk-live-secret",
                nested={"access_token": "abc", "message_body": "do not leak"},
                plain_value="safe",
            ):
                pass

        merged = "\n".join(captured.output)
        self.assertIn("a***@example.com", merged)
        self.assertIn("[content]", merged)
        self.assertIn("[redacted]", merged)
        self.assertIn("plain_value", merged)
        self.assertIn("safe", merged)
        self.assertNotIn("alice@example.com", merged)
        self.assertNotIn("my private text", merged)
        self.assertNotIn("sk-live-secret", merged)
        self.assertNotIn("do not leak", merged)

    def test_trace_span_includes_context_fields(self) -> None:
        request_token = request_id_var.set("req-123")
        user_token = user_id_var.set("user-abc")
        partner_token = partner_id_var.set("partner-def")
        session_token = session_id_var.set("session-xyz")
        mode_token = mode_var.set("DECK")
        self.addCleanup(lambda: request_id_var.reset(request_token))
        self.addCleanup(lambda: user_id_var.reset(user_token))
        self.addCleanup(lambda: partner_id_var.reset(partner_token))
        self.addCleanup(lambda: session_id_var.reset(session_token))
        self.addCleanup(lambda: mode_var.reset(mode_token))

        with self.assertLogs("app.services.trace_span", level="INFO") as captured:
            with trace_span("trace-context"):
                pass

        merged = "\n".join(captured.output)
        self.assertIn("request_id=req-123", merged)
        self.assertIn("context_user_id", merged)
        self.assertIn("user-abc", merged)
        self.assertIn("context_partner_id", merged)
        self.assertIn("partner-def", merged)
        self.assertIn("context_session_id", merged)
        self.assertIn("session-xyz", merged)
        self.assertIn("context_mode", merged)
        self.assertIn("DECK", merged)


if __name__ == "__main__":
    unittest.main()
