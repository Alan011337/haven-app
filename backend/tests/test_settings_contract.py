from __future__ import annotations

from types import SimpleNamespace

from app.core._settings_impl import Settings
from app.core.settings_contract import validate_settings_contract


def _build_settings(**overrides):
    base = {
        "POSTHOG_ENABLED": False,
        "POSTHOG_API_KEY": "",
        "POSTHOG_HOST": "",
        "AI_ROUTER_SHARED_STATE_BACKEND": "memory",
        "AI_ROUTER_REDIS_URL": "",
        "ABUSE_GUARD_STORE_BACKEND": "memory",
        "ABUSE_GUARD_REDIS_URL": "",
        "ALLOWLIST_ENFORCED": False,
        "ALLOWED_TEST_EMAILS": "",
        "ALLOWED_TEST_EMAILS_JSON": "",
        "FEATURE_FLAGS_JSON": "{}",
        "FEATURE_KILL_SWITCHES_JSON": "{}",
        "WEBSOCKET_ENABLED": True,
        "WS_MAX_CONNECTIONS_PER_USER": 1,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_validate_settings_contract_passes_on_valid_defaults() -> None:
    errors = validate_settings_contract(_build_settings())
    assert errors == []


def test_validate_settings_contract_detects_missing_redis_url() -> None:
    errors = validate_settings_contract(
        _build_settings(AI_ROUTER_SHARED_STATE_BACKEND="redis", AI_ROUTER_REDIS_URL="")
    )
    assert any("AI_ROUTER_SHARED_STATE_BACKEND=redis" in reason for reason in errors)


def test_validate_settings_contract_accepts_abuse_guard_redis_url_for_ai_router_shared_state() -> None:
    errors = validate_settings_contract(
        _build_settings(
            AI_ROUTER_SHARED_STATE_BACKEND="redis",
            AI_ROUTER_REDIS_URL="",
            ABUSE_GUARD_REDIS_URL="redis://redis.internal:6379/1",
        )
    )
    assert errors == []


def test_validate_settings_contract_detects_invalid_feature_flag_json() -> None:
    errors = validate_settings_contract(_build_settings(FEATURE_FLAGS_JSON="[]"))
    assert any("FEATURE_FLAGS_JSON" in reason for reason in errors)


def test_validate_settings_contract_detects_allowlist_misconfig() -> None:
    errors = validate_settings_contract(_build_settings(ALLOWLIST_ENFORCED=True))
    assert any("ALLOWLIST_ENFORCED requires" in reason for reason in errors)


def test_settings_defaults_to_memory_shared_state_backend() -> None:
    settings = Settings(
        _env_file=None,
        DATABASE_URL="sqlite:///./test.db",
        OPENAI_API_KEY="test-key",
        SECRET_KEY="01234567890123456789012345678901",
    )

    assert settings.AI_ROUTER_SHARED_STATE_BACKEND == "memory"
    assert settings.AI_ROUTER_REDIS_URL is None
