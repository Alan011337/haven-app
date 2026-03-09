"""Structured logging filter that auto-injects request_id and user_id from context."""
import logging
import hashlib
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


def should_sample_event(*, sample_key: str, sample_rate: float) -> bool:
    """Deterministic sampling helper to cap high-volume log streams."""
    try:
        rate = float(sample_rate)
    except (TypeError, ValueError):
        rate = 1.0
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    digest = hashlib.sha256(sample_key.encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") / float(0xFFFFFFFF)
    return bucket <= rate


class StructuredContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get() or "-"
        record.user_id = user_id_var.get() or "-"
        record.partner_id = partner_id_var.get() or "-"
        record.session_id = session_id_var.get() or "-"
        record.mode = mode_var.get() or "-"
        route = route_var.get() or "-"
        record.route = route[:160]
        record.status_code = status_code_var.get() or "-"
        record.latency_ms = latency_ms_var.get() or "-"
        return True
