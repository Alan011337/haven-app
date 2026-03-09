"""Tests for PII redaction (log/trace safety)."""

import unittest
from app.core.log_redaction import (
    redact_content,
    redact_email,
    redact_exception_reason,
    redact_ip,
    redact_name,
)


class TestLogRedaction(unittest.TestCase):
    def test_redact_email_masks_middle(self) -> None:
        self.assertEqual(redact_email("alice@example.com"), "a***@example.com")
        self.assertEqual(redact_email("bob+tag@test.co"), "b***@test.co")

    def test_redact_email_empty_or_none(self) -> None:
        self.assertEqual(redact_email(""), "")
        self.assertEqual(redact_email(None), "")

    def test_redact_email_no_pii_leak(self) -> None:
        out = redact_email("secret.user@company.org")
        self.assertNotIn("secret", out)
        self.assertNotIn("user", out)
        self.assertIn("@company.org", out)

    def test_redact_name_placeholder(self) -> None:
        self.assertEqual(redact_name("Alice", min_visible=0), "[name]")
        self.assertEqual(redact_name("", min_visible=0), "")

    def test_redact_name_partial(self) -> None:
        self.assertEqual(redact_name("Alice", min_visible=1), "A****")

    def test_redact_content_redacted(self) -> None:
        self.assertEqual(redact_content("long journal text here", max_visible=0), "[content]")

    def test_redact_content_length_hint(self) -> None:
        out = redact_content("hello world", max_visible=5)
        self.assertTrue(out.startswith("hello"))
        self.assertIn("len=11", out)

    def test_redact_ip_ipv4(self) -> None:
        self.assertEqual(redact_ip("203.0.113.42"), "203.0.x.x")

    def test_redact_ip_ipv6(self) -> None:
        self.assertEqual(
            redact_ip("2001:db8::1"),
            "2001:0db8:x:x:x:x:x:x",
        )

    def test_redact_ip_invalid(self) -> None:
        self.assertEqual(redact_ip("not-an-ip"), "[ip]")
        self.assertEqual(redact_ip(None), "[ip]")

    def test_redact_exception_reason_from_exception(self) -> None:
        reason = redact_exception_reason(RuntimeError("token=abc123"))
        self.assertEqual(reason, "runtimeerror")

    def test_redact_exception_reason_from_string(self) -> None:
        reason = redact_exception_reason("openai timeout: key=abc123")
        self.assertEqual(reason, "openai_timeout_key")
