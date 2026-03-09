"""
PII redaction for logs and traces.
Sensitive data must not appear in log/trace output (P0-H / security baseline).
"""

import ipaddress
import re
from typing import Optional

# Email: leave first char and domain suffix, redact middle (e.g. a***@example.com)
_EMAIL_PATTERN = re.compile(r"\b([a-zA-Z0-9_])([a-zA-Z0-9_.+-]*)(@[a-zA-Z0-9][a-zA-Z0-9.-]*\.[a-zA-Z]{2,})\b")


def redact_email(value: Optional[str]) -> str:
    """Redact email for logging: keep first char + domain, mask middle."""
    if not value or not isinstance(value, str):
        return ""
    return _EMAIL_PATTERN.sub(r"\1***\3", value)


def redact_ip(value: Optional[str]) -> str:
    """Redact client IP for logging."""
    if not value or not isinstance(value, str):
        return "[ip]"

    normalized = value.strip()
    if not normalized:
        return "[ip]"

    try:
        parsed = ipaddress.ip_address(normalized)
    except ValueError:
        return "[ip]"

    if isinstance(parsed, ipaddress.IPv4Address):
        octets = parsed.exploded.split(".")
        return f"{octets[0]}.{octets[1]}.x.x"

    hextets = parsed.exploded.split(":")
    return f"{hextets[0]}:{hextets[1]}:x:x:x:x:x:x"


def redact_name(value: Optional[str], min_visible: int = 0) -> str:
    """Redact name: return fixed placeholder to avoid leaking PII."""
    if not value or not isinstance(value, str):
        return ""
    if min_visible <= 0:
        return "[name]"
    if len(value) <= min_visible:
        return "[name]"
    return value[:min_visible] + "*" * (len(value) - min_visible)


def redact_content(value: Optional[str], max_visible: int = 0) -> str:
    """Redact free-text content (e.g. journal/card body). Return length hint only or [redacted]."""
    if not value or not isinstance(value, str):
        return ""
    if max_visible <= 0:
        return "[content]"
    if len(value) <= max_visible:
        return value[:max_visible] + ("..." if len(value) > max_visible else "")
    return value[:max_visible] + "... [len=" + str(len(value)) + "]"


def redact_exception_reason(value: Exception | str | None) -> str:
    """
    Convert exception/message into a stable, non-sensitive reason key.
    Examples:
      RuntimeError("token leaked") -> "runtimeerror"
      "openai timeout: key=..."    -> "openai_timeout_key"
    """
    if value is None:
        return "unknown_error"
    if isinstance(value, Exception):
        raw = value.__class__.__name__
        normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", raw.strip().lower()).strip("_")
    elif isinstance(value, str):
        # Keep only alpha tokens from free-form strings to avoid leaking ids/tokens.
        tokens = re.findall(r"(?<![a-zA-Z0-9])[a-zA-Z]{2,}(?![a-zA-Z0-9])", value.strip().lower())
        normalized = "_".join(tokens[:4]).strip("_")
    else:
        normalized = re.sub(r"[^a-zA-Z0-9_]+", "_", str(value).strip().lower()).strip("_")
    return normalized or "unknown_error"
