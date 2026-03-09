"""Grouped settings manifest for domain-based env governance."""

from __future__ import annotations

from typing import Any


SETTINGS_DOMAIN_MANIFEST: dict[str, tuple[str, ...]] = {
    "core": (
        "DATABASE_URL",
        "OPENAI_API_KEY",
        "SECRET_KEY",
        "CORS_ORIGINS",
    ),
    "ai_router": (
        "AI_ROUTER_PRIMARY_PROVIDER",
        "AI_ROUTER_ENABLE_FALLBACK",
        "AI_ROUTER_MAX_TOTAL_ATTEMPTS",
        "AI_ROUTER_MAX_ELAPSED_MS",
    ),
    "notification_outbox": (
        "NOTIFICATION_OUTBOX_ENABLED",
        "NOTIFICATION_OUTBOX_MAX_ATTEMPTS",
        "NOTIFICATION_OUTBOX_RETRY_BASE_SECONDS",
        "NOTIFICATION_OUTBOX_CLAIM_LIMIT",
    ),
    "observability": (
        "METRICS_REQUIRE_AUTH",
        "HEALTH_READINESS_CACHE_TTL_SECONDS",
    ),
}


def validate_manifest_against_settings(source: Any) -> dict[str, tuple[str, ...]]:
    """Return missing settings attrs by domain (empty tuple means complete)."""
    report: dict[str, tuple[str, ...]] = {}
    for domain, keys in SETTINGS_DOMAIN_MANIFEST.items():
        missing = tuple(key for key in keys if not hasattr(source, key))
        report[domain] = missing
    return report

