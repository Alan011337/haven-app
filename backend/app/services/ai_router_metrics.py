"""Shared metric label/key sanitizers for AI router runtime metrics."""

from __future__ import annotations

import re

_LABEL_PATTERN = re.compile(r"^[a-z0-9_]+$")
_DENY_TOKENS = (
    "user_id",
    "request_id",
    "email",
    "phone",
    "address",
    "session",
    "token",
    "jwt",
    "password",
    "secret",
    "api_key",
    "raw_model",
    "journal",
    "content",
)


def sanitize_metric_key(raw: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    return cleaned or "unknown"


def sanitize_metric_label(
    *,
    raw: str,
    allowlist: set[str],
    unknown_bucket: str = "unknown",
) -> str:
    normalized = sanitize_metric_key(raw)
    for token in _DENY_TOKENS:
        if token in normalized:
            return unknown_bucket
    if not _LABEL_PATTERN.match(normalized):
        return unknown_bucket
    if len(normalized) > 32:
        return unknown_bucket
    if normalized not in allowlist:
        return unknown_bucket
    return normalized
