from __future__ import annotations

import logging
import re
import time
import uuid
from contextlib import contextmanager
import json
from typing import Iterator

from app.core.config import settings
from app.core.log_redaction import redact_content, redact_email, redact_ip
from app.middleware.request_context import (
    mode_var,
    partner_id_var,
    request_id_var,
    session_id_var,
    user_id_var,
)

logger = logging.getLogger(__name__)
_SECRET_FIELD_HINTS = (
    "token",
    "secret",
    "password",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
)
_EMAIL_FIELD_HINTS = ("email",)
_CONTENT_FIELD_HINTS = ("content", "text", "body", "message", "prompt", "journal")
_IP_FIELD_HINTS = ("ip", "client_ip", "remote_addr")
_DEFAULT_OTEL_ATTRIBUTE_ALLOWLIST = frozenset(
    {
        "context_user_id",
        "context_partner_id",
        "context_session_id",
        "context_mode",
        "token",
        "user_email",
        "email",
        "route",
        "endpoint",
        "action",
        "event_name",
        "reason",
        "result",
        "status_code",
        "latency_ms",
        "provider",
        "model",
        "retry",
        "attempt",
        "source",
    }
)

try:
    from opentelemetry import trace as _otel_trace
except Exception:  # pragma: no cover - optional dependency
    _otel_trace = None


def _key_tokens(key: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", key.lower()) if token}


def _matches_key_hint(normalized_key: str, hints: tuple[str, ...]) -> bool:
    tokens = _key_tokens(normalized_key)
    for hint in hints:
        hint_key = hint.lower()
        if hint_key in tokens:
            return True
        hint_tokens = _key_tokens(hint_key)
        if hint_tokens and hint_tokens.issubset(tokens):
            return True
    return False


def _sanitize_trace_value(key: str, value: object) -> object:
    normalized_key = key.lower()

    if isinstance(value, dict):
        sanitized_dict: dict[str, object] = {}
        for nested_key, nested_value in value.items():
            sanitized_dict[str(nested_key)] = _sanitize_trace_value(str(nested_key), nested_value)
        return sanitized_dict

    if isinstance(value, (list, tuple, set)):
        return [_sanitize_trace_value(key, item) for item in value]

    if _matches_key_hint(normalized_key, _SECRET_FIELD_HINTS):
        return "[redacted]"

    if not isinstance(value, str):
        return value

    if _matches_key_hint(normalized_key, _EMAIL_FIELD_HINTS):
        return redact_email(value)

    if _matches_key_hint(normalized_key, _IP_FIELD_HINTS):
        return redact_ip(value)

    if _matches_key_hint(normalized_key, _CONTENT_FIELD_HINTS):
        return redact_content(value, max_visible=0)

    return value


def _sanitize_trace_fields(fields: dict[str, object]) -> dict[str, object]:
    return {key: _sanitize_trace_value(key, value) for key, value in fields.items()}


def _trace_otel_enabled() -> bool:
    if not bool(getattr(settings, "OTEL_TRACING_ENABLED", False)):
        return False
    return _otel_trace is not None


def _normalize_otel_attribute_value(value: object) -> str | int | float | bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        return value
    try:
        encoded = json.dumps(value, ensure_ascii=True, sort_keys=True, default=str)
    except Exception:
        encoded = str(value)
    if len(encoded) > 1024:
        return encoded[:1021] + "..."
    return encoded


def _otel_attribute_allowlist() -> set[str]:
    raw = getattr(settings, "TRACE_SPAN_OTEL_ATTRIBUTE_ALLOWLIST", "")
    if not isinstance(raw, str) or not raw.strip():
        return set(_DEFAULT_OTEL_ATTRIBUTE_ALLOWLIST)
    parsed = {
        token.strip().lower()
        for token in raw.split(",")
        if token and token.strip()
    }
    return parsed or set(_DEFAULT_OTEL_ATTRIBUTE_ALLOWLIST)


def _otel_max_attributes() -> int:
    raw = getattr(settings, "TRACE_SPAN_OTEL_MAX_ATTRIBUTES", 24)
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 24


def _select_otel_fields(fields: dict[str, object]) -> dict[str, object]:
    allowlist = _otel_attribute_allowlist()
    max_count = _otel_max_attributes()
    selected: dict[str, object] = {}
    for key in sorted(fields.keys()):
        normalized = key.lower()
        if normalized not in allowlist:
            continue
        selected[key] = fields[key]
        if len(selected) >= max_count:
            break
    return selected


def _set_otel_attributes(span: object, *, request_id: str, name: str, fields: dict[str, object]) -> None:
    if span is None or not hasattr(span, "set_attribute"):
        return
    span.set_attribute("haven.span.name", name)
    span.set_attribute("haven.request_id", request_id or "")
    for key, value in _select_otel_fields(fields).items():
        attr_key = f"haven.{key.lower()}"
        span.set_attribute(attr_key, _normalize_otel_attribute_value(value))


@contextmanager
def trace_span(name: str, **fields: object) -> Iterator[str]:
    """Minimal trace span logger for API->DB->AI chain observability."""
    span_id = uuid.uuid4().hex[:12]
    request_id = request_id_var.get() or ""
    enriched_fields = {
        "context_user_id": user_id_var.get() or "-",
        "context_partner_id": partner_id_var.get() or "-",
        "context_session_id": session_id_var.get() or "-",
        "context_mode": mode_var.get() or "-",
    }
    enriched_fields.update(fields)
    safe_fields = _sanitize_trace_fields(enriched_fields)
    started = time.perf_counter()
    logger.info(
        "trace_span_start span=%s request_id=%s name=%s fields=%s",
        span_id,
        request_id,
        name,
        safe_fields,
    )
    if _trace_otel_enabled():
        tracer = _otel_trace.get_tracer("haven.trace_span")
        with tracer.start_as_current_span(name) as otel_span:
            _set_otel_attributes(otel_span, request_id=request_id, name=name, fields=safe_fields)
            try:
                yield span_id
            finally:
                elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
                logger.info(
                    "trace_span_end span=%s request_id=%s name=%s elapsed_ms=%s",
                    span_id,
                    request_id,
                    name,
                    elapsed_ms,
                )
                if hasattr(otel_span, "set_attribute"):
                    otel_span.set_attribute("haven.elapsed_ms", elapsed_ms)
        return

    try:
        yield span_id
    finally:
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        logger.info(
            "trace_span_end span=%s request_id=%s name=%s elapsed_ms=%s",
            span_id,
            request_id,
            name,
            elapsed_ms,
        )
