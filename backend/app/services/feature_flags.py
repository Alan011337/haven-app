from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.core.runtime_switches import get_runtime_feature_switches

logger = logging.getLogger(__name__)

DEFAULT_FEATURE_FLAGS: dict[str, bool] = {
    "growth_referral_enabled": False,
    "growth_ab_experiment_enabled": False,
    "growth_pricing_experiment_enabled": False,
    "growth_reengagement_hooks_enabled": False,
    "growth_activation_dashboard_enabled": True,
    "growth_onboarding_quest_enabled": True,
    "growth_sync_nudges_enabled": True,
    "growth_first_delight_enabled": True,
    "weekly_review_v1": False,
    "repair_flow_v1": False,
    "dynamic_background_enabled": False,
    "websocket_realtime_enabled": True,
    "webpush_enabled": False,
    "email_notifications_enabled": True,
    "timeline_cursor_enabled": True,
    "safety_mode_enabled": True,
}

DEFAULT_KILL_SWITCHES: dict[str, bool] = {
    "disable_referral_funnel": False,
    "disable_growth_events_ingest": False,
    "disable_growth_ab_experiment": False,
    "disable_pricing_experiment": False,
    "disable_growth_reengagement_hooks": False,
    "disable_growth_activation_dashboard": False,
    "disable_growth_onboarding_quest": False,
    "disable_growth_sync_nudges": False,
    "disable_growth_first_delight": False,
    "disable_weekly_review_v1": False,
    "disable_repair_flow_v1": False,
    "disable_dynamic_background": False,
    "disable_websocket_realtime": False,
    "disable_webpush": False,
    "disable_email_notifications": False,
    "disable_timeline_cursor": False,
    "disable_safety_mode": False,
}

KILL_SWITCH_TO_FLAG: dict[str, str] = {
    "disable_referral_funnel": "growth_referral_enabled",
    "disable_growth_ab_experiment": "growth_ab_experiment_enabled",
    "disable_pricing_experiment": "growth_pricing_experiment_enabled",
    "disable_growth_reengagement_hooks": "growth_reengagement_hooks_enabled",
    "disable_growth_activation_dashboard": "growth_activation_dashboard_enabled",
    "disable_growth_onboarding_quest": "growth_onboarding_quest_enabled",
    "disable_growth_sync_nudges": "growth_sync_nudges_enabled",
    "disable_growth_first_delight": "growth_first_delight_enabled",
    "disable_weekly_review_v1": "weekly_review_v1",
    "disable_repair_flow_v1": "repair_flow_v1",
    "disable_dynamic_background": "dynamic_background_enabled",
    "disable_websocket_realtime": "websocket_realtime_enabled",
    "disable_webpush": "webpush_enabled",
    "disable_email_notifications": "email_notifications_enabled",
    "disable_timeline_cursor": "timeline_cursor_enabled",
    "disable_safety_mode": "safety_mode_enabled",
}


@dataclass(frozen=True)
class ResolvedFeatureFlags:
    flags: dict[str, bool]
    kill_switches: dict[str, bool]


def _coerce_bool_map(
    *,
    raw_json: str,
    default_map: dict[str, bool],
    source_name: str,
) -> dict[str, bool]:
    cleaned = (raw_json or "").strip()
    if not cleaned:
        return default_map.copy()

    try:
        payload = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning(
            "feature_flag_config_parse_failed source=%s using_defaults=true",
            source_name,
        )
        return default_map.copy()

    if not isinstance(payload, dict):
        logger.warning(
            "feature_flag_config_parse_failed source=%s reason=not_object using_defaults=true",
            source_name,
        )
        return default_map.copy()

    result = default_map.copy()
    for key, value in payload.items():
        if not isinstance(key, str):
            continue
        if not isinstance(value, bool):
            continue
        result[key.strip()] = value
    return result


def resolve_feature_flags(
    *,
    has_partner: bool,
) -> ResolvedFeatureFlags:
    flags = _coerce_bool_map(
        raw_json=settings.FEATURE_FLAGS_JSON,
        default_map=DEFAULT_FEATURE_FLAGS,
        source_name="FEATURE_FLAGS_JSON",
    )
    kill_switches = _coerce_bool_map(
        raw_json=settings.FEATURE_KILL_SWITCHES_JSON,
        default_map=DEFAULT_KILL_SWITCHES,
        source_name="FEATURE_KILL_SWITCHES_JSON",
    )

    runtime_switches = get_runtime_feature_switches()
    flags["websocket_realtime_enabled"] = runtime_switches.websocket_enabled
    flags["webpush_enabled"] = runtime_switches.webpush_enabled and runtime_switches.push_notifications_enabled
    flags["email_notifications_enabled"] = runtime_switches.email_notifications_enabled
    flags["timeline_cursor_enabled"] = runtime_switches.timeline_cursor_enabled
    flags["safety_mode_enabled"] = runtime_switches.safety_mode_enabled

    if not has_partner:
        flags["growth_referral_enabled"] = False
        flags["growth_reengagement_hooks_enabled"] = False

    for kill_switch, disabled in kill_switches.items():
        if not disabled:
            continue
        target_flag = KILL_SWITCH_TO_FLAG.get(kill_switch)
        if target_flag:
            flags[target_flag] = False

    return ResolvedFeatureFlags(
        flags=flags,
        kill_switches=kill_switches,
    )


def get_feature_flag(key: str, *, has_partner: bool, default: bool = False) -> bool:
    resolved = resolve_feature_flags(has_partner=has_partner)
    return bool(resolved.flags.get(key, default))


def list_feature_flags_for_client(*, has_partner: bool) -> dict[str, Any]:
    resolved = resolve_feature_flags(has_partner=has_partner)
    return {
        "flags": resolved.flags,
        "kill_switches": resolved.kill_switches,
        "has_partner_context": has_partner,
    }
