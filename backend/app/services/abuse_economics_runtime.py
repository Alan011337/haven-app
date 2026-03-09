from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_PATH = REPO_ROOT / "docs" / "security" / "abuse-economics-policy.json"

_WS_STORM_COUNTER_KEYS: tuple[str, ...] = (
    "connections_rejected_invalid_user_id",
    "connections_rejected_missing_token",
    "connections_rejected_invalid_token",
    "connections_rejected_user_not_found",
    "connections_rejected_global_cap",
    "connections_rejected_per_user_cap",
    "messages_rate_limited",
    "messages_payload_too_large",
    "messages_backoff_active",
    "messages_blocked_other",
)


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, parsed)


def _load_policy(policy_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(policy_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "policy_file_missing"
    except json.JSONDecodeError:
        return None, "policy_file_invalid_json"
    except OSError:
        return None, "policy_file_unreadable"

    if not isinstance(payload, dict):
        return None, "policy_payload_invalid"
    return payload, None


def _rate_limit_action_count(rate_limit_snapshot: dict[str, Any], action: str) -> int:
    blocked_by_action = (
        rate_limit_snapshot.get("blocked_by_action")
        if isinstance(rate_limit_snapshot, dict)
        else {}
    )
    if not isinstance(blocked_by_action, dict):
        return 0
    return _safe_int(blocked_by_action.get(action))


def _ws_counter_count(ws_runtime_snapshot: dict[str, Any], counter_key: str) -> int:
    counters = (
        ws_runtime_snapshot.get("counters")
        if isinstance(ws_runtime_snapshot, dict)
        else {}
    )
    if not isinstance(counters, dict):
        return 0
    return _safe_int(counters.get(counter_key))


def _resolve_observed_events(
    *,
    vector_id: str,
    rate_limit_snapshot: dict[str, Any],
    ws_runtime_snapshot: dict[str, Any],
) -> tuple[int, str]:
    if vector_id == "token_drain_journal_analysis":
        return _rate_limit_action_count(rate_limit_snapshot, "journal_create"), "rate_limit.blocked_by_action.journal_create"
    if vector_id == "ws_storm":
        total = sum(_ws_counter_count(ws_runtime_snapshot, key) for key in _WS_STORM_COUNTER_KEYS)
        return total, "ws_runtime.counters.rejected_or_blocked"
    if vector_id == "pairing_bruteforce":
        return _rate_limit_action_count(rate_limit_snapshot, "pairing_attempt"), "rate_limit.blocked_by_action.pairing_attempt"
    if vector_id == "push_notification_spam":
        total = _rate_limit_action_count(
            rate_limit_snapshot, "journal_create"
        ) + _rate_limit_action_count(rate_limit_snapshot, "card_response_create")
        return total, "rate_limit.blocked_by_action.journal_create+card_response_create"
    if vector_id == "signup_abuse":
        return _rate_limit_action_count(rate_limit_snapshot, "login"), "rate_limit.blocked_by_action.login"
    return 0, "unmapped_vector"


def _project_daily_events(*, observed_events: int, uptime_seconds: int) -> float:
    safe_observed = max(0, int(observed_events))
    if safe_observed <= 0:
        return 0.0
    safe_uptime = max(1, int(uptime_seconds))
    projected = (float(safe_observed) / float(safe_uptime)) * 86400.0
    return round(max(0.0, projected), 6)


def _resolve_vector_status(*, utilization_ratio: float | None) -> str:
    if utilization_ratio is None:
        return "ok"
    if utilization_ratio >= 1.0:
        return "block"
    if utilization_ratio >= 0.8:
        return "warn"
    return "ok"


def build_abuse_economics_runtime_snapshot(
    *,
    rate_limit_snapshot: dict[str, Any],
    ws_runtime_snapshot: dict[str, Any],
    uptime_seconds: int,
    policy_path: Path = DEFAULT_POLICY_PATH,
) -> dict[str, Any]:
    policy, policy_error = _load_policy(policy_path)
    if policy is None:
        return {
            "status": "insufficient_data",
            "uptime_seconds": max(0, int(uptime_seconds)),
            "policy_path": str(policy_path),
            "evaluation": {
                "status": "insufficient_data",
                "reasons": [policy_error or "policy_unavailable"],
                "signal_present": False,
            },
            "vectors": [],
            "estimated_daily_total_usd": 0.0,
            "thresholds": {},
        }

    vectors = policy.get("vectors")
    if not isinstance(vectors, list) or not vectors:
        return {
            "status": "insufficient_data",
            "uptime_seconds": max(0, int(uptime_seconds)),
            "policy_path": str(policy_path),
            "policy_schema_version": str(policy.get("schema_version") or "unknown"),
            "policy_artifact_kind": str(policy.get("artifact_kind") or "unknown"),
            "evaluation": {
                "status": "insufficient_data",
                "reasons": ["vectors_missing"],
                "signal_present": False,
            },
            "vectors": [],
            "estimated_daily_total_usd": 0.0,
            "thresholds": {},
        }

    thresholds = policy.get("escalation_thresholds") if isinstance(policy.get("escalation_thresholds"), dict) else {}
    warn_daily_total_usd = _safe_float(thresholds.get("warn_daily_total_usd"))
    block_daily_total_usd = _safe_float(thresholds.get("block_daily_total_usd"))

    safe_uptime_seconds = max(0, int(uptime_seconds))
    vector_rows: list[dict[str, Any]] = []
    vector_reasons: list[str] = []
    estimated_daily_total_usd = 0.0
    observed_total_events = 0

    for vector in vectors:
        if not isinstance(vector, dict):
            continue
        vector_id = str(vector.get("id") or "").strip()
        if not vector_id:
            continue

        observed_events, signal_source = _resolve_observed_events(
            vector_id=vector_id,
            rate_limit_snapshot=rate_limit_snapshot,
            ws_runtime_snapshot=ws_runtime_snapshot,
        )
        observed_total_events += observed_events

        projected_daily_events = _project_daily_events(
            observed_events=observed_events,
            uptime_seconds=safe_uptime_seconds,
        )
        unit_cost_usd = _safe_float(vector.get("unit_cost_usd"))
        estimated_daily_cost_usd = round(projected_daily_events * unit_cost_usd, 6)
        estimated_daily_total_usd += estimated_daily_cost_usd

        max_events_per_user_per_day = _safe_int(vector.get("max_events_per_user_per_day"))
        max_events_per_ip_per_day = _safe_int(vector.get("max_events_per_ip_per_day"))

        denominator = max_events_per_ip_per_day or max_events_per_user_per_day
        utilization_ratio = (
            round(projected_daily_events / float(denominator), 6)
            if denominator > 0
            else None
        )
        vector_status = _resolve_vector_status(utilization_ratio=utilization_ratio)
        if vector_status in {"warn", "block"}:
            vector_reasons.append(f"{vector_id}_{vector_status}")

        vector_rows.append(
            {
                "id": vector_id,
                "description": str(vector.get("description") or ""),
                "signal_source": signal_source,
                "observed_events_total": observed_events,
                "projected_daily_events": projected_daily_events,
                "unit_cost_usd": unit_cost_usd,
                "estimated_daily_cost_usd": estimated_daily_cost_usd,
                "max_events_per_user_per_day": max_events_per_user_per_day,
                "max_events_per_ip_per_day": max_events_per_ip_per_day,
                "utilization_ratio": utilization_ratio,
                "status": vector_status,
            }
        )

    estimated_daily_total_usd = round(estimated_daily_total_usd, 6)

    reasons = list(vector_reasons)
    overall_status = "ok"
    if block_daily_total_usd > 0 and estimated_daily_total_usd >= block_daily_total_usd:
        overall_status = "block"
        reasons.append("daily_total_cost_above_block_threshold")
    elif warn_daily_total_usd > 0 and estimated_daily_total_usd >= warn_daily_total_usd:
        overall_status = "warn"
        reasons.append("daily_total_cost_above_warn_threshold")

    if overall_status != "block":
        if any(row.get("status") == "block" for row in vector_rows):
            overall_status = "block"
        elif any(row.get("status") == "warn" for row in vector_rows):
            overall_status = "warn"

    return {
        "status": overall_status,
        "uptime_seconds": safe_uptime_seconds,
        "policy_path": str(policy_path),
        "policy_schema_version": str(policy.get("schema_version") or "unknown"),
        "policy_artifact_kind": str(policy.get("artifact_kind") or "unknown"),
        "observed_total_events": observed_total_events,
        "estimated_daily_total_usd": estimated_daily_total_usd,
        "thresholds": {
            "warn_daily_total_usd": warn_daily_total_usd,
            "block_daily_total_usd": block_daily_total_usd,
        },
        "vectors": vector_rows,
        "evaluation": {
            "status": overall_status,
            "reasons": sorted(set(reasons)),
            "signal_present": observed_total_events > 0,
        },
    }
