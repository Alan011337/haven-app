"""Shared HTTP policy constants/helpers for API middleware."""

from __future__ import annotations

IDEMPOTENCY_REQUIRED_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})

IDEMPOTENCY_EXEMPT_PATHS = frozenset(
    {
        "/api/auth/token",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/v2/auth/token",
        "/api/v2/auth/refresh",
        "/api/v2/auth/logout",
        "/api/billing/webhooks/stripe",
        "/api/billing/webhooks/appstore",
        "/api/billing/webhooks/googleplay",
    }
)

SECURITY_HEADER_EXCLUDED_PATHS = frozenset(
    {
        "/docs",
        "/docs/oauth2-redirect",
        "/openapi.json",
        "/redoc",
    }
)

SECURITY_RESPONSE_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
}


def normalize_path(path: str) -> str:
    """Normalize request path to avoid trailing-slash mismatch checks."""
    if not path:
        return "/"
    if path == "/":
        return path
    return path.rstrip("/")


def is_idempotency_exempt_path(path: str) -> bool:
    return normalize_path(path) in IDEMPOTENCY_EXEMPT_PATHS


def is_security_header_excluded_path(path: str) -> bool:
    return normalize_path(path) in SECURITY_HEADER_EXCLUDED_PATHS

