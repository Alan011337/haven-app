#!/usr/bin/env python3
"""Validate backend environment variables before startup."""

from __future__ import annotations

import base64
import binascii
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_ROOT / ".env"

REQUIRED_KEYS = (
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "SECRET_KEY",
)

OPTIONAL_KEYS = (
    "ENV",
    "ENVIRONMENT",
    "POSTHOG_API_KEY",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "BILLING_STRIPE_SECRET_KEY",
    "VAPID_PRIVATE_KEY",
    "GEMINI_API_KEY",
    "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED",
    "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED",
    "AI_ROUTER_PRIMARY_PROVIDER",
    "AI_ROUTER_FALLBACK_PROVIDER",
    "AI_ROUTER_ENABLE_FALLBACK",
    "AI_ROUTER_GEMINI_MODEL",
    "AI_ROUTER_SHARED_STATE_BACKEND",
    "AI_ROUTER_REDIS_URL",
    "AI_SCHEMA_COMPLIANCE_MIN",
    "AI_HALLUCINATION_PROXY_MAX",
    "AI_DRIFT_SCORE_MAX",
    "AI_COST_MAX_USD_PER_ACTIVE_COUPLE",
    "AI_TOKEN_BUDGET_DAILY",
    "AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS",
    "FIELD_LEVEL_ENCRYPTION_ENABLED",
    "FIELD_LEVEL_ENCRYPTION_KEY",
    "NOTIFICATION_COOLDOWN_SECONDS",
    "JOURNAL_RATE_LIMIT_COUNT",
    "JOURNAL_RATE_LIMIT_WINDOW_SECONDS",
    "JOURNAL_RATE_LIMIT_IP_COUNT",
    "JOURNAL_RATE_LIMIT_DEVICE_COUNT",
    "JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT",
    "CARD_RESPONSE_RATE_LIMIT_COUNT",
    "CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
    "CARD_RESPONSE_RATE_LIMIT_IP_COUNT",
    "CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT",
    "CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT",
    "RATE_LIMIT_DEVICE_HEADER",
    "PAIRING_ATTEMPT_RATE_LIMIT_COUNT",
    "PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS",
    "PAIRING_FAILURE_COOLDOWN_THRESHOLD",
    "PAIRING_FAILURE_COOLDOWN_SECONDS",
    "PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT",
    "PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS",
    "PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD",
    "PAIRING_IP_FAILURE_COOLDOWN_SECONDS",
    "WS_MAX_CONNECTIONS_PER_USER",
    "WS_MAX_CONNECTIONS_GLOBAL",
    "WS_MESSAGE_RATE_LIMIT_COUNT",
    "WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS",
    "WS_MESSAGE_BACKOFF_SECONDS",
    "WS_MAX_PAYLOAD_BYTES",
    "ABUSE_GUARD_STORE_BACKEND",
    "ABUSE_GUARD_REDIS_URL",
    "ABUSE_GUARD_REDIS_KEY_PREFIX",
    "WEBSOCKET_ENABLED",
    "WEBPUSH_ENABLED",
    "EMAIL_NOTIFICATIONS_ENABLED",
    "TIMELINE_CURSOR_ENABLED",
    "SAFETY_MODE_ENABLED",
    "SLO_GATE_HEALTH_SLO_URL",
    "SLO_GATE_HEALTH_SLO_FILE",
    "SLO_GATE_BEARER_TOKEN",
    "SLO_GATE_TIMEOUT_SECONDS",
    "SLO_GATE_REQUIRE_SUFFICIENT_DATA",
    "RELEASE_GATE_ALLOW_MISSING_SLO_URL",
    "RELEASE_GATE_HOTFIX_OVERRIDE",
    "RELEASE_GATE_OVERRIDE_REASON",
    "RELEASE_GATE_OVERRIDE_REASON_PATTERN",
    "RELEASE_TARGET_TIER",
    "RELEASE_INTENT",
    "CANARY_GUARD_HEALTH_SLO_URL",
    "CANARY_GUARD_BEARER_TOKEN",
    "CANARY_GUARD_DURATION_SECONDS",
    "CANARY_GUARD_INTERVAL_SECONDS",
    "CANARY_GUARD_MAX_FAILURES",
    "CANARY_GUARD_REQUIRE_SUFFICIENT_DATA",
    "CANARY_GUARD_TIMEOUT_SECONDS",
    "CANARY_GUARD_TARGET_PERCENT",
    "CANARY_GUARD_ROLLOUT_HOOK_URL",
    "CANARY_GUARD_ROLLBACK_HOOK_URL",
    "CANARY_GUARD_HOOK_BEARER_TOKEN",
    "CANARY_GUARD_HOOK_TIMEOUT_SECONDS",
    "HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET",
    "HEALTH_WS_MESSAGE_PASS_RATE_TARGET",
    "HEALTH_WS_SLI_MIN_CONNECTION_ATTEMPTS",
    "HEALTH_WS_SLI_MIN_MESSAGES",
    "HEALTH_WS_BURN_RATE_FAST_THRESHOLD",
    "HEALTH_WS_BURN_RATE_SLOW_THRESHOLD",
    "HEALTH_WS_BURN_RATE_MIN_CONNECTION_ATTEMPTS",
    "HEALTH_WS_BURN_RATE_MIN_MESSAGES",
    "BILLING_STRIPE_WEBHOOK_SECRET",
    "BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS",
    "AUDIT_LOG_RETENTION_DAYS",
    "DATA_EXPORT_EXPIRY_DAYS",
    "DATA_SOFT_DELETE_ENABLED",
    "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS",
    "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS",
    "DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS",
    "P0_DRILL_EVIDENCE_MAX_AGE_DAYS",
    "DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS",
    "BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS",
    "BILLING_RECON_EVIDENCE_MAX_AGE_DAYS",
    "AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS",
    "LAUNCH_SIGNOFF_MAX_AGE_DAYS",
    "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF",
    "CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS",
    "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE",
    "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_WORKFLOW_FILE",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_BRANCH",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_NAME",
    "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_FILE",
)

_ENV_NAME_ALIASES = {
    "dev": "development",
    "development": "development",
    "alpha": "alpha",
    "staging": "staging",
    "stage": "staging",
    "prod": "production",
    "production": "production",
}


def _is_placeholder(value: str) -> bool:
    lowered = value.strip().lower()
    return lowered in {"", "changeme", "your-key", "replace-me", "example"}


def _validate_database_url(value: str) -> str | None:
    parsed = urlparse(value)
    if (
        parsed.scheme == "sqlite"
        or parsed.scheme.startswith("postgres")
        or parsed.scheme.startswith("postgresql")
    ):
        return None
    return "DATABASE_URL must start with postgres://, postgresql://, or sqlite://"


def _validate_secret_key(value: str) -> str | None:
    if len(value.strip()) < 32:
        return "SECRET_KEY should be at least 32 characters"
    return None


def _validate_positive_int(name: str, raw_value: str) -> str | None:
    try:
        value = int(raw_value)
    except ValueError:
        return f"{name} must be an integer"
    if value <= 0:
        return f"{name} must be greater than 0"
    return None


def _validate_positive_float(name: str, raw_value: str) -> str | None:
    try:
        value = float(raw_value)
    except ValueError:
        return f"{name} must be a number"
    if value <= 0:
        return f"{name} must be greater than 0"
    return None


def _validate_redis_url(name: str, value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"redis", "rediss"}:
        return f"{name} must start with redis:// or rediss://"
    if not parsed.netloc:
        return f"{name} must include host"
    return None


def _first_present_redis_env(*names: str) -> tuple[str | None, str]:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return name, value
    return None, ""


def _validate_http_url(name: str, value: str) -> str | None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        return f"{name} must start with http:// or https://"
    if not parsed.netloc:
        return f"{name} must include host"
    return None


def _validate_ratio_0_to_1(name: str, raw_value: str) -> str | None:
    try:
        value = float(raw_value)
    except ValueError:
        return f"{name} must be a number"
    if value <= 0 or value > 1:
        return f"{name} must be > 0 and <= 1"
    return None


def _validate_percent_0_to_100(name: str, raw_value: str) -> str | None:
    try:
        value = float(raw_value)
    except ValueError:
        return f"{name} must be a number"
    if value <= 0 or value > 100:
        return f"{name} must be > 0 and <= 100"
    return None


def _validate_bool_string(name: str, raw_value: str) -> str | None:
    if raw_value.lower() not in {"1", "0", "true", "false", "yes", "no", "on", "off"}:
        return f"{name} must be one of: 1/0/true/false/yes/no/on/off"
    return None


def _normalize_env_name(raw_value: str) -> str:
    return _ENV_NAME_ALIASES.get(raw_value.strip().lower(), "")


def _validate_encryption_key(name: str, raw_value: str) -> str | None:
    key = raw_value.strip()
    if not key:
        return f"{name} is required"
    if len(key) != 44:
        return f"{name} must be a 44-char urlsafe-base64 key"
    try:
        decoded = base64.urlsafe_b64decode(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError, binascii.Error):
        return f"{name} must be valid urlsafe-base64"
    if len(decoded) != 32:
        return f"{name} must decode to 32 bytes"
    return None


def _validate_ai_provider(name: str, raw_value: str) -> str | None:
    if raw_value.strip().lower() not in {"openai", "gemini"}:
        return f"{name} must be one of: openai/gemini"
    return None


def _validate_release_gate_ai_quality_evidence_source(raw_value: str) -> str | None:
    if raw_value.strip().lower() not in {"local_snapshot", "daily_artifact"}:
        return (
            "RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE must be one of: "
            "local_snapshot/daily_artifact"
        )
    return None


def _validate_release_target_tier(raw_value: str) -> str | None:
    if raw_value.strip().lower() not in {"tier_0", "tier_1"}:
        return "RELEASE_TARGET_TIER must be `tier_0` or `tier_1`"
    return None


def _validate_release_intent(raw_value: str) -> str | None:
    if raw_value.strip().lower() not in {"feature", "bugfix", "security", "hotfix"}:
        return (
            "RELEASE_INTENT must be one of: "
            "feature/bugfix/security/hotfix"
        )
    return None


def _validate_regex(name: str, raw_value: str) -> str | None:
    import re

    try:
        re.compile(raw_value)
    except re.error:
        return f"{name} must be a valid regex pattern"
    return None


def _is_enabled_bool(raw_value: str) -> bool:
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, raw_value = stripped.split("=", 1)
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    _load_env_file(ENV_FILE)

    missing: list[str] = []
    invalid: list[str] = []

    for key in REQUIRED_KEYS:
        raw = os.getenv(key)
        if raw is None or _is_placeholder(raw):
            missing.append(key)

    database_url = os.getenv("DATABASE_URL", "")
    if database_url and "DATABASE_URL" not in missing:
        issue = _validate_database_url(database_url)
        if issue:
            invalid.append(issue)

    secret_key = os.getenv("SECRET_KEY", "")
    if secret_key and "SECRET_KEY" not in missing:
        issue = _validate_secret_key(secret_key)
        if issue:
            invalid.append(issue)

    notification_cooldown = os.getenv("NOTIFICATION_COOLDOWN_SECONDS", "").strip()
    if notification_cooldown:
        issue = _validate_positive_float("NOTIFICATION_COOLDOWN_SECONDS", notification_cooldown)
        if issue:
            invalid.append(issue)

    slo_gate_url = os.getenv("SLO_GATE_HEALTH_SLO_URL", "").strip()
    if slo_gate_url:
        issue = _validate_http_url("SLO_GATE_HEALTH_SLO_URL", slo_gate_url)
        if issue:
            invalid.append(issue)

    slo_gate_payload_file = os.getenv("SLO_GATE_HEALTH_SLO_FILE", "").strip()
    if slo_gate_payload_file:
        payload_path = Path(slo_gate_payload_file)
        if not payload_path.is_absolute():
            payload_path = (BACKEND_ROOT / payload_path).resolve()
        if not payload_path.exists():
            invalid.append(
                "SLO_GATE_HEALTH_SLO_FILE must point to an existing JSON file path"
            )
        elif not payload_path.is_file():
            invalid.append("SLO_GATE_HEALTH_SLO_FILE must be a file path")

    slo_gate_timeout = os.getenv("SLO_GATE_TIMEOUT_SECONDS", "").strip()
    if slo_gate_timeout:
        issue = _validate_positive_float("SLO_GATE_TIMEOUT_SECONDS", slo_gate_timeout)
        if issue:
            invalid.append(issue)

    slo_gate_require_sufficient = os.getenv("SLO_GATE_REQUIRE_SUFFICIENT_DATA", "").strip()
    if slo_gate_require_sufficient:
        issue = _validate_bool_string("SLO_GATE_REQUIRE_SUFFICIENT_DATA", slo_gate_require_sufficient)
        if issue:
            invalid.append(issue)

    release_gate_allow_missing_slo = os.getenv("RELEASE_GATE_ALLOW_MISSING_SLO_URL", "").strip()
    if release_gate_allow_missing_slo:
        issue = _validate_bool_string(
            "RELEASE_GATE_ALLOW_MISSING_SLO_URL",
            release_gate_allow_missing_slo,
        )
        if issue:
            invalid.append(issue)

    release_gate_hotfix_override = os.getenv("RELEASE_GATE_HOTFIX_OVERRIDE", "").strip()
    if release_gate_hotfix_override:
        issue = _validate_bool_string(
            "RELEASE_GATE_HOTFIX_OVERRIDE",
            release_gate_hotfix_override,
        )
        if issue:
            invalid.append(issue)

    release_gate_override_reason = os.getenv("RELEASE_GATE_OVERRIDE_REASON", "").strip()
    if release_gate_override_reason and len(release_gate_override_reason) > 300:
        invalid.append("RELEASE_GATE_OVERRIDE_REASON is too long (max 300 chars)")

    release_gate_override_reason_pattern = os.getenv("RELEASE_GATE_OVERRIDE_REASON_PATTERN", "").strip()
    if release_gate_override_reason_pattern:
        issue = _validate_regex(
            "RELEASE_GATE_OVERRIDE_REASON_PATTERN",
            release_gate_override_reason_pattern,
        )
        if issue:
            invalid.append(issue)

    release_target_tier = os.getenv("RELEASE_TARGET_TIER", "").strip()
    if release_target_tier:
        issue = _validate_release_target_tier(release_target_tier)
        if issue:
            invalid.append(issue)

    release_intent = os.getenv("RELEASE_INTENT", "").strip()
    if release_intent:
        issue = _validate_release_intent(release_intent)
        if issue:
            invalid.append(issue)

    canary_guard_health_url = os.getenv("CANARY_GUARD_HEALTH_SLO_URL", "").strip()
    if canary_guard_health_url:
        issue = _validate_http_url("CANARY_GUARD_HEALTH_SLO_URL", canary_guard_health_url)
        if issue:
            invalid.append(issue)

    canary_guard_rollout_hook_url = os.getenv("CANARY_GUARD_ROLLOUT_HOOK_URL", "").strip()
    if canary_guard_rollout_hook_url:
        issue = _validate_http_url("CANARY_GUARD_ROLLOUT_HOOK_URL", canary_guard_rollout_hook_url)
        if issue:
            invalid.append(issue)

    canary_guard_rollback_hook_url = os.getenv("CANARY_GUARD_ROLLBACK_HOOK_URL", "").strip()
    if canary_guard_rollback_hook_url:
        issue = _validate_http_url("CANARY_GUARD_ROLLBACK_HOOK_URL", canary_guard_rollback_hook_url)
        if issue:
            invalid.append(issue)

    canary_guard_timeout = os.getenv("CANARY_GUARD_TIMEOUT_SECONDS", "").strip()
    if canary_guard_timeout:
        issue = _validate_positive_float("CANARY_GUARD_TIMEOUT_SECONDS", canary_guard_timeout)
        if issue:
            invalid.append(issue)

    canary_guard_hook_timeout = os.getenv("CANARY_GUARD_HOOK_TIMEOUT_SECONDS", "").strip()
    if canary_guard_hook_timeout:
        issue = _validate_positive_float("CANARY_GUARD_HOOK_TIMEOUT_SECONDS", canary_guard_hook_timeout)
        if issue:
            invalid.append(issue)

    canary_guard_target_percent = os.getenv("CANARY_GUARD_TARGET_PERCENT", "").strip()
    if canary_guard_target_percent:
        issue = _validate_percent_0_to_100(
            "CANARY_GUARD_TARGET_PERCENT",
            canary_guard_target_percent,
        )
        if issue:
            invalid.append(issue)

    canary_guard_require_sufficient = os.getenv("CANARY_GUARD_REQUIRE_SUFFICIENT_DATA", "").strip()
    if canary_guard_require_sufficient:
        issue = _validate_bool_string(
            "CANARY_GUARD_REQUIRE_SUFFICIENT_DATA",
            canary_guard_require_sufficient,
        )
        if issue:
            invalid.append(issue)

    release_gate_allow_missing_launch_signoff = os.getenv(
        "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF",
        "",
    ).strip()
    if release_gate_allow_missing_launch_signoff:
        issue = _validate_bool_string(
            "RELEASE_GATE_ALLOW_MISSING_LAUNCH_SIGNOFF",
            release_gate_allow_missing_launch_signoff,
        )
        if issue:
            invalid.append(issue)

    release_gate_allow_missing_cuj_synthetic_evidence = os.getenv(
        "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE",
        "",
    ).strip()
    if release_gate_allow_missing_cuj_synthetic_evidence:
        issue = _validate_bool_string(
            "RELEASE_GATE_ALLOW_MISSING_CUJ_SYNTHETIC_EVIDENCE",
            release_gate_allow_missing_cuj_synthetic_evidence,
        )
        if issue:
            invalid.append(issue)

    release_gate_allow_missing_ai_quality_snapshot = os.getenv(
        "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE",
        "",
    ).strip()
    if release_gate_allow_missing_ai_quality_snapshot:
        issue = _validate_bool_string(
            "RELEASE_GATE_ALLOW_MISSING_AI_QUALITY_SNAPSHOT_EVIDENCE",
            release_gate_allow_missing_ai_quality_snapshot,
        )
        if issue:
            invalid.append(issue)

    release_gate_ai_quality_evidence_source = os.getenv(
        "RELEASE_GATE_AI_QUALITY_EVIDENCE_SOURCE",
        "",
    ).strip()
    if release_gate_ai_quality_evidence_source:
        issue = _validate_release_gate_ai_quality_evidence_source(
            release_gate_ai_quality_evidence_source
        )
        if issue:
            invalid.append(issue)

    release_gate_ai_quality_evidence_repo = os.getenv(
        "RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO",
        "",
    ).strip()
    if release_gate_ai_quality_evidence_repo:
        if "/" not in release_gate_ai_quality_evidence_repo:
            invalid.append(
                "RELEASE_GATE_AI_QUALITY_EVIDENCE_REPO must be owner/repository format"
            )

    release_gate_ai_quality_evidence_branch = os.getenv(
        "RELEASE_GATE_AI_QUALITY_EVIDENCE_BRANCH",
        "",
    ).strip()
    if release_gate_ai_quality_evidence_branch and len(release_gate_ai_quality_evidence_branch) > 128:
        invalid.append("RELEASE_GATE_AI_QUALITY_EVIDENCE_BRANCH is too long (max 128 chars)")

    release_gate_ai_quality_evidence_artifact_name = os.getenv(
        "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_NAME",
        "",
    ).strip()
    if release_gate_ai_quality_evidence_artifact_name and len(
        release_gate_ai_quality_evidence_artifact_name
    ) > 128:
        invalid.append(
            "RELEASE_GATE_AI_QUALITY_EVIDENCE_ARTIFACT_NAME is too long (max 128 chars)"
        )

    canary_guard_duration = os.getenv("CANARY_GUARD_DURATION_SECONDS", "").strip()
    if canary_guard_duration:
        issue = _validate_positive_int("CANARY_GUARD_DURATION_SECONDS", canary_guard_duration)
        if issue:
            invalid.append(issue)

    canary_guard_interval = os.getenv("CANARY_GUARD_INTERVAL_SECONDS", "").strip()
    if canary_guard_interval:
        issue = _validate_positive_int("CANARY_GUARD_INTERVAL_SECONDS", canary_guard_interval)
        if issue:
            invalid.append(issue)

    canary_guard_max_failures = os.getenv("CANARY_GUARD_MAX_FAILURES", "").strip()
    if canary_guard_max_failures:
        issue = _validate_positive_int("CANARY_GUARD_MAX_FAILURES", canary_guard_max_failures)
        if issue:
            invalid.append(issue)

    if canary_guard_duration and canary_guard_interval:
        try:
            duration = int(canary_guard_duration)
            interval = int(canary_guard_interval)
            if interval > duration:
                invalid.append(
                    "CANARY_GUARD_INTERVAL_SECONDS must be <= CANARY_GUARD_DURATION_SECONDS"
                )
        except ValueError:
            pass

    health_ws_connection_accept_rate_target = os.getenv(
        "HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET", ""
    ).strip()
    if health_ws_connection_accept_rate_target:
        issue = _validate_ratio_0_to_1(
            "HEALTH_WS_CONNECTION_ACCEPT_RATE_TARGET",
            health_ws_connection_accept_rate_target,
        )
        if issue:
            invalid.append(issue)

    health_ws_message_pass_rate_target = os.getenv("HEALTH_WS_MESSAGE_PASS_RATE_TARGET", "").strip()
    if health_ws_message_pass_rate_target:
        issue = _validate_ratio_0_to_1(
            "HEALTH_WS_MESSAGE_PASS_RATE_TARGET",
            health_ws_message_pass_rate_target,
        )
        if issue:
            invalid.append(issue)

    health_ws_burn_rate_fast_threshold = os.getenv("HEALTH_WS_BURN_RATE_FAST_THRESHOLD", "").strip()
    if health_ws_burn_rate_fast_threshold:
        issue = _validate_positive_float(
            "HEALTH_WS_BURN_RATE_FAST_THRESHOLD",
            health_ws_burn_rate_fast_threshold,
        )
        if issue:
            invalid.append(issue)

    health_ws_burn_rate_slow_threshold = os.getenv("HEALTH_WS_BURN_RATE_SLOW_THRESHOLD", "").strip()
    if health_ws_burn_rate_slow_threshold:
        issue = _validate_positive_float(
            "HEALTH_WS_BURN_RATE_SLOW_THRESHOLD",
            health_ws_burn_rate_slow_threshold,
        )
        if issue:
            invalid.append(issue)

    if health_ws_burn_rate_fast_threshold and health_ws_burn_rate_slow_threshold:
        try:
            fast_threshold = float(health_ws_burn_rate_fast_threshold)
            slow_threshold = float(health_ws_burn_rate_slow_threshold)
            if fast_threshold < slow_threshold:
                invalid.append(
                    "HEALTH_WS_BURN_RATE_FAST_THRESHOLD must be >= "
                    "HEALTH_WS_BURN_RATE_SLOW_THRESHOLD"
                )
        except ValueError:
            pass

    rate_limit_device_header = os.getenv("RATE_LIMIT_DEVICE_HEADER", "").strip()
    if rate_limit_device_header == "":
        pass
    elif len(rate_limit_device_header) > 64:
        invalid.append("RATE_LIMIT_DEVICE_HEADER is too long (max 64 chars)")

    for rate_key in (
        "JOURNAL_RATE_LIMIT_COUNT",
        "JOURNAL_RATE_LIMIT_WINDOW_SECONDS",
        "JOURNAL_RATE_LIMIT_IP_COUNT",
        "JOURNAL_RATE_LIMIT_DEVICE_COUNT",
        "JOURNAL_RATE_LIMIT_PARTNER_PAIR_COUNT",
        "CARD_RESPONSE_RATE_LIMIT_COUNT",
        "CARD_RESPONSE_RATE_LIMIT_WINDOW_SECONDS",
        "CARD_RESPONSE_RATE_LIMIT_IP_COUNT",
        "CARD_RESPONSE_RATE_LIMIT_DEVICE_COUNT",
        "CARD_RESPONSE_RATE_LIMIT_PARTNER_PAIR_COUNT",
        "PAIRING_ATTEMPT_RATE_LIMIT_COUNT",
        "PAIRING_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS",
        "PAIRING_FAILURE_COOLDOWN_THRESHOLD",
        "PAIRING_FAILURE_COOLDOWN_SECONDS",
        "PAIRING_IP_ATTEMPT_RATE_LIMIT_COUNT",
        "PAIRING_IP_ATTEMPT_RATE_LIMIT_WINDOW_SECONDS",
        "PAIRING_IP_FAILURE_COOLDOWN_THRESHOLD",
        "PAIRING_IP_FAILURE_COOLDOWN_SECONDS",
        "WS_MAX_CONNECTIONS_PER_USER",
        "WS_MAX_CONNECTIONS_GLOBAL",
        "WS_MESSAGE_RATE_LIMIT_COUNT",
        "WS_MESSAGE_RATE_LIMIT_WINDOW_SECONDS",
        "WS_MESSAGE_BACKOFF_SECONDS",
        "WS_MAX_PAYLOAD_BYTES",
        "HEALTH_WS_SLI_MIN_CONNECTION_ATTEMPTS",
        "HEALTH_WS_SLI_MIN_MESSAGES",
        "HEALTH_WS_BURN_RATE_MIN_CONNECTION_ATTEMPTS",
        "HEALTH_WS_BURN_RATE_MIN_MESSAGES",
        "BILLING_STRIPE_WEBHOOK_TOLERANCE_SECONDS",
        "AUDIT_LOG_RETENTION_DAYS",
        "DATA_EXPORT_EXPIRY_DAYS",
        "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS",
        "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS",
        "DATA_SOFT_DELETE_PURGE_EVIDENCE_MAX_AGE_DAYS",
        "P0_DRILL_EVIDENCE_MAX_AGE_DAYS",
        "DATA_RIGHTS_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS",
        "BILLING_FIRE_DRILL_EVIDENCE_MAX_AGE_DAYS",
        "BILLING_RECON_EVIDENCE_MAX_AGE_DAYS",
        "AUDIT_RETENTION_EVIDENCE_MAX_AGE_DAYS",
        "LAUNCH_SIGNOFF_MAX_AGE_DAYS",
        "CUJ_SYNTHETIC_EVIDENCE_MAX_AGE_HOURS",
        "AI_TOKEN_BUDGET_DAILY",
    ):
        raw_value = os.getenv(rate_key, "").strip()
        if not raw_value:
            continue
        issue = _validate_positive_int(rate_key, raw_value)
        if issue:
            invalid.append(issue)

    soft_delete_trash_days = os.getenv("DATA_SOFT_DELETE_TRASH_RETENTION_DAYS", "").strip()
    soft_delete_purge_days = os.getenv("DATA_SOFT_DELETE_PURGE_RETENTION_DAYS", "").strip()
    if soft_delete_trash_days and soft_delete_purge_days:
        try:
            trash_days = int(soft_delete_trash_days)
            purge_days = int(soft_delete_purge_days)
            if purge_days < trash_days:
                invalid.append(
                    "DATA_SOFT_DELETE_PURGE_RETENTION_DAYS must be >= "
                    "DATA_SOFT_DELETE_TRASH_RETENTION_DAYS"
                )
        except ValueError:
            pass

    data_soft_delete_enabled = os.getenv("DATA_SOFT_DELETE_ENABLED", "").strip()
    if data_soft_delete_enabled:
        issue = _validate_bool_string("DATA_SOFT_DELETE_ENABLED", data_soft_delete_enabled)
        if issue:
            invalid.append(issue)

    ai_dynamic_context_injection_enabled = os.getenv(
        "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED",
        "",
    ).strip()
    if ai_dynamic_context_injection_enabled:
        issue = _validate_bool_string(
            "AI_DYNAMIC_CONTEXT_INJECTION_ENABLED",
            ai_dynamic_context_injection_enabled,
        )
        if issue:
            invalid.append(issue)

    ai_persona_runtime_guardrail_enabled = os.getenv(
        "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED",
        "",
    ).strip()
    if ai_persona_runtime_guardrail_enabled:
        issue = _validate_bool_string(
            "AI_PERSONA_RUNTIME_GUARDRAIL_ENABLED",
            ai_persona_runtime_guardrail_enabled,
        )
        if issue:
            invalid.append(issue)

    ai_router_enable_fallback = os.getenv("AI_ROUTER_ENABLE_FALLBACK", "").strip()
    if ai_router_enable_fallback:
        issue = _validate_bool_string("AI_ROUTER_ENABLE_FALLBACK", ai_router_enable_fallback)
        if issue:
            invalid.append(issue)

    ai_router_primary_provider = os.getenv("AI_ROUTER_PRIMARY_PROVIDER", "").strip()
    if ai_router_primary_provider:
        issue = _validate_ai_provider("AI_ROUTER_PRIMARY_PROVIDER", ai_router_primary_provider)
        if issue:
            invalid.append(issue)

    ai_router_fallback_provider = os.getenv("AI_ROUTER_FALLBACK_PROVIDER", "").strip()
    if ai_router_fallback_provider:
        issue = _validate_ai_provider("AI_ROUTER_FALLBACK_PROVIDER", ai_router_fallback_provider)
        if issue:
            invalid.append(issue)

    ai_router_gemini_model = os.getenv("AI_ROUTER_GEMINI_MODEL", "").strip()
    if ai_router_gemini_model and len(ai_router_gemini_model) > 128:
        invalid.append("AI_ROUTER_GEMINI_MODEL is too long (max 128 chars)")

    ai_router_shared_state_backend = os.getenv("AI_ROUTER_SHARED_STATE_BACKEND", "").strip().lower()
    if ai_router_shared_state_backend and ai_router_shared_state_backend not in {"memory", "redis"}:
        invalid.append("AI_ROUTER_SHARED_STATE_BACKEND must be 'memory' or 'redis'")

    ai_router_redis_url_name, ai_router_redis_url = _first_present_redis_env(
        "AI_ROUTER_REDIS_URL",
        "REDIS_URL",
        "ABUSE_GUARD_REDIS_URL",
    )
    if ai_router_shared_state_backend == "redis":
        if not ai_router_redis_url:
            invalid.append(
                "AI_ROUTER_SHARED_STATE_BACKEND=redis requires AI_ROUTER_REDIS_URL, REDIS_URL, or ABUSE_GUARD_REDIS_URL"
            )
        else:
            issue = _validate_redis_url(ai_router_redis_url_name or "AI_ROUTER_REDIS_URL", ai_router_redis_url)
            if issue:
                invalid.append(issue)

    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_api_key and _is_placeholder(gemini_api_key):
        invalid.append("GEMINI_API_KEY cannot be placeholder value")

    gemini_required = False
    if ai_router_primary_provider.strip().lower() == "gemini":
        gemini_required = True
    elif _is_enabled_bool(ai_router_enable_fallback) and ai_router_fallback_provider.strip().lower() == "gemini":
        gemini_required = True

    if gemini_required and _is_placeholder(gemini_api_key):
        missing.append("GEMINI_API_KEY")

    ai_schema_compliance_min = os.getenv("AI_SCHEMA_COMPLIANCE_MIN", "").strip()
    if ai_schema_compliance_min:
        issue = _validate_percent_0_to_100("AI_SCHEMA_COMPLIANCE_MIN", ai_schema_compliance_min)
        if issue:
            invalid.append(issue)

    ai_hallucination_proxy_max = os.getenv("AI_HALLUCINATION_PROXY_MAX", "").strip()
    if ai_hallucination_proxy_max:
        issue = _validate_ratio_0_to_1("AI_HALLUCINATION_PROXY_MAX", ai_hallucination_proxy_max)
        if issue:
            invalid.append(issue)

    ai_drift_score_max = os.getenv("AI_DRIFT_SCORE_MAX", "").strip()
    if ai_drift_score_max:
        issue = _validate_ratio_0_to_1("AI_DRIFT_SCORE_MAX", ai_drift_score_max)
        if issue:
            invalid.append(issue)

    ai_cost_max_usd_per_active_couple = os.getenv("AI_COST_MAX_USD_PER_ACTIVE_COUPLE", "").strip()
    if ai_cost_max_usd_per_active_couple:
        issue = _validate_positive_float(
            "AI_COST_MAX_USD_PER_ACTIVE_COUPLE",
            ai_cost_max_usd_per_active_couple,
        )
        if issue:
            invalid.append(issue)

    ai_quality_snapshot_max_age_hours = os.getenv("AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS", "").strip()
    if ai_quality_snapshot_max_age_hours:
        issue = _validate_positive_float(
            "AI_QUALITY_SNAPSHOT_MAX_AGE_HOURS",
            ai_quality_snapshot_max_age_hours,
        )
        if issue:
            invalid.append(issue)

    field_level_encryption_enabled = os.getenv("FIELD_LEVEL_ENCRYPTION_ENABLED", "").strip()
    if field_level_encryption_enabled:
        issue = _validate_bool_string(
            "FIELD_LEVEL_ENCRYPTION_ENABLED",
            field_level_encryption_enabled,
        )
        if issue:
            invalid.append(issue)

    if _is_enabled_bool(field_level_encryption_enabled):
        field_level_encryption_key = os.getenv("FIELD_LEVEL_ENCRYPTION_KEY", "").strip()
        issue = _validate_encryption_key("FIELD_LEVEL_ENCRYPTION_KEY", field_level_encryption_key)
        if issue:
            if _is_placeholder(field_level_encryption_key):
                missing.append("FIELD_LEVEL_ENCRYPTION_KEY")
            else:
                invalid.append(issue)

    env_name_raw = os.getenv("ENV", "development")
    env_name = env_name_raw.strip().lower()
    if env_name == "production" and not _is_enabled_bool(field_level_encryption_enabled):
        invalid.append("FIELD_LEVEL_ENCRYPTION_ENABLED must be true when ENV=production")

    environment_raw = os.getenv("ENVIRONMENT", "").strip()
    if environment_raw:
        normalized_env = _normalize_env_name(env_name_raw)
        normalized_environment = _normalize_env_name(environment_raw)
        if not normalized_environment:
            invalid.append("ENVIRONMENT must be one of: development/alpha/staging/production")
        elif normalized_env and normalized_env != normalized_environment:
            invalid.append(
                "ENV and ENVIRONMENT must resolve to the same environment when both are set"
            )

    abuse_guard_backend = os.getenv("ABUSE_GUARD_STORE_BACKEND", "memory").strip().lower()
    if abuse_guard_backend and abuse_guard_backend not in {"memory", "redis"}:
        invalid.append("ABUSE_GUARD_STORE_BACKEND must be 'memory' or 'redis'")

    if abuse_guard_backend == "redis":
        redis_url = os.getenv("ABUSE_GUARD_REDIS_URL", "").strip()
        if not redis_url:
            invalid.append("ABUSE_GUARD_REDIS_URL is required when ABUSE_GUARD_STORE_BACKEND=redis")
        else:
            issue = _validate_redis_url("ABUSE_GUARD_REDIS_URL", redis_url)
            if issue:
                invalid.append(issue)

    print("[backend env check]")
    print(f"  loaded_from: {ENV_FILE if ENV_FILE.exists() else 'process env'}")

    if missing:
        print("  missing_required:")
        for key in missing:
            print(f"    - {key}")

    if invalid:
        print("  invalid_values:")
        for issue in invalid:
            print(f"    - {issue}")

    print("  optional_present:")
    for key in OPTIONAL_KEYS:
        print(f"    - {key}: {'yes' if os.getenv(key) else 'no'}")

    if missing or invalid:
        print("result: fail")
        return 1

    print("result: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
