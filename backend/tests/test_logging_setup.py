import io
import logging
import unittest

from app.core.logging_setup import configure_structured_logging
from app.core.structured_logger import StructuredContextFilter
from app.middleware.request_context import (
    latency_ms_var,
    mode_var,
    partner_id_var,
    request_id_var,
    route_var,
    session_id_var,
    status_code_var,
    user_id_var,
)


class LoggingSetupTests(unittest.TestCase):
    def _preserve_logger(self, name: str) -> logging.Logger:
        logger = logging.getLogger(name)
        state = {
            "handlers": list(logger.handlers),
            "filters": list(logger.filters),
            "level": logger.level,
            "propagate": logger.propagate,
        }

        def restore() -> None:
            logger.handlers = state["handlers"]
            logger.filters = state["filters"]
            logger.setLevel(state["level"])
            logger.propagate = state["propagate"]

        self.addCleanup(restore)
        return logger

    def test_configure_structured_logging_is_idempotent(self) -> None:
        logger = self._preserve_logger("uvicorn.error")
        handler = logging.StreamHandler(io.StringIO())
        logger.handlers = [handler]
        logger.filters = []
        logger.propagate = False

        configure_structured_logging()
        configure_structured_logging()

        logger_filter_count = sum(
            isinstance(entry, StructuredContextFilter) for entry in logger.filters
        )
        handler_filter_count = sum(
            isinstance(entry, StructuredContextFilter) for entry in handler.filters
        )
        self.assertEqual(logger_filter_count, 1)
        self.assertEqual(handler_filter_count, 1)

    def test_configure_structured_logging_injects_request_and_user_ids(self) -> None:
        stream = io.StringIO()
        logger = self._preserve_logger("uvicorn.error")
        handler = logging.StreamHandler(stream)
        handler.setFormatter(
            logging.Formatter(
                "%(request_id)s %(user_id)s %(partner_id)s %(session_id)s %(mode)s %(route)s %(status_code)s %(latency_ms)s %(message)s"
            )
        )
        logger.handlers = [handler]
        logger.filters = []
        logger.setLevel(logging.INFO)
        logger.propagate = False

        configure_structured_logging()

        request_token = request_id_var.set("req-123")
        user_token = user_id_var.set("user-789")
        partner_token = partner_id_var.set("partner-456")
        session_token = session_id_var.set("session-333")
        mode_token = mode_var.set("DAILY_RITUAL")
        route_token = route_var.set("/api/journals")
        status_token = status_code_var.set("201")
        latency_token = latency_ms_var.set("12.500")
        self.addCleanup(lambda: request_id_var.reset(request_token))
        self.addCleanup(lambda: user_id_var.reset(user_token))
        self.addCleanup(lambda: partner_id_var.reset(partner_token))
        self.addCleanup(lambda: session_id_var.reset(session_token))
        self.addCleanup(lambda: mode_var.reset(mode_token))
        self.addCleanup(lambda: route_var.reset(route_token))
        self.addCleanup(lambda: status_code_var.reset(status_token))
        self.addCleanup(lambda: latency_ms_var.reset(latency_token))

        logger.info("request-context-ok")
        output = stream.getvalue().strip()
        self.assertIn(
            "req-123 user-789 partner-456 session-333 DAILY_RITUAL /api/journals 201 12.500 request-context-ok",
            output,
        )


if __name__ == "__main__":
    unittest.main()
