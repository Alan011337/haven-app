from __future__ import annotations

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


class StructuredLoggingContractTests(unittest.TestCase):
    def test_filter_injects_required_runtime_fields(self) -> None:
        filter_instance = StructuredContextFilter()
        record = logging.LogRecord(
            name="haven.test",
            level=logging.INFO,
            pathname=__file__,
            lineno=10,
            msg="test",
            args=(),
            exc_info=None,
        )
        tokens = [
            request_id_var.set("req-1"),
            user_id_var.set("u-1"),
            partner_id_var.set("p-1"),
            session_id_var.set("s-1"),
            mode_var.set("deck"),
            route_var.set("/api/cards/respond"),
            status_code_var.set(200),
            latency_ms_var.set(88),
        ]
        try:
            self.assertTrue(filter_instance.filter(record))
            self.assertEqual(record.request_id, "req-1")
            self.assertEqual(record.user_id, "u-1")
            self.assertEqual(record.partner_id, "p-1")
            self.assertEqual(record.session_id, "s-1")
            self.assertEqual(record.mode, "deck")
            self.assertEqual(record.route, "/api/cards/respond")
            self.assertEqual(record.status_code, 200)
            self.assertEqual(record.latency_ms, 88)
        finally:
            request_id_var.reset(tokens[0])
            user_id_var.reset(tokens[1])
            partner_id_var.reset(tokens[2])
            session_id_var.reset(tokens[3])
            mode_var.reset(tokens[4])
            route_var.reset(tokens[5])
            status_code_var.reset(tokens[6])
            latency_ms_var.reset(tokens[7])

    def test_configure_structured_logging_is_idempotent(self) -> None:
        root_logger = logging.getLogger("")
        before = len([f for f in root_logger.filters if isinstance(f, StructuredContextFilter)])
        configure_structured_logging()
        configure_structured_logging()
        after = len([f for f in root_logger.filters if isinstance(f, StructuredContextFilter)])
        self.assertLessEqual(after - before, 1)


if __name__ == "__main__":
    unittest.main()

