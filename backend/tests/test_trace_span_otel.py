import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services import trace_span as trace_span_module  # noqa: E402


class _FakeSpanContext:
    def __init__(self, span):
        self._span = span

    def __enter__(self):
        return self._span

    def __exit__(self, exc_type, exc, tb):
        return False


class TraceSpanOtelTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_enabled = settings.OTEL_TRACING_ENABLED

    def tearDown(self) -> None:
        settings.OTEL_TRACING_ENABLED = self._original_enabled

    def test_trace_span_falls_back_when_otel_dependency_missing(self) -> None:
        settings.OTEL_TRACING_ENABLED = True
        with patch.object(trace_span_module, "_otel_trace", None):
            with trace_span_module.trace_span("trace.fallback", user_email="owner@example.com"):
                pass

    def test_trace_span_sets_sanitized_otel_attributes_when_enabled(self) -> None:
        settings.OTEL_TRACING_ENABLED = True
        fake_span = MagicMock()
        fake_tracer = MagicMock()
        fake_tracer.start_as_current_span.return_value = _FakeSpanContext(fake_span)
        fake_otel = MagicMock()
        fake_otel.get_tracer.return_value = fake_tracer

        with patch.object(trace_span_module, "_otel_trace", fake_otel):
            with trace_span_module.trace_span(
                "trace.otel",
                token="top-secret-token",
                user_email="owner@example.com",
                untrusted_detail="drop-me",
            ):
                pass

        fake_otel.get_tracer.assert_called_once_with("haven.trace_span")
        set_calls = [call.args for call in fake_span.set_attribute.call_args_list]
        self.assertIn(("haven.token", "[redacted]"), set_calls)
        email_attrs = [args for args in set_calls if args and args[0] == "haven.user_email"]
        self.assertEqual(len(email_attrs), 1)
        self.assertNotEqual(email_attrs[0][1], "owner@example.com")
        unknown_attrs = [args for args in set_calls if args and args[0] == "haven.untrusted_detail"]
        self.assertEqual(unknown_attrs, [])


if __name__ == "__main__":
    unittest.main()
