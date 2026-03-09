from __future__ import annotations

from dataclasses import dataclass

_PARTNER_EVENT_LATENCY_BUCKETS_MS = (10, 25, 50, 100, 250, 500, 1000, 2000, 5000)


def _counter_value(counters: dict[str, int], key: str) -> int:
    try:
        return max(0, int(counters.get(key, 0)))
    except (TypeError, ValueError):
        return 0


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _window_label(window_seconds: int) -> str:
    safe_window_seconds = max(1, int(window_seconds))
    if safe_window_seconds % 3600 == 0:
        return f"{safe_window_seconds // 3600}h"
    if safe_window_seconds % 60 == 0:
        return f"{safe_window_seconds // 60}m"
    return f"{safe_window_seconds}s"


def _safe_burn_rate(error_total: int, total: int, *, target_success_rate: float) -> float | None:
    error_budget = 1.0 - float(target_success_rate)
    if total <= 0 or error_budget <= 0:
        return None
    error_rate = max(0.0, float(error_total) / float(total))
    return round(error_rate / error_budget, 6)


def _estimate_latency_p95_ms(*, counters: dict[str, int]) -> int | None:
    total = _counter_value(counters, "partner_event_delivery_latency_samples_total")
    if total <= 0:
        return None
    target = max(1, int(total * 0.95))
    cumulative = 0
    for bucket_ms in _PARTNER_EVENT_LATENCY_BUCKETS_MS:
        cumulative += _counter_value(
            counters,
            f"partner_event_delivery_latency_bucket_le_{bucket_ms}ms_total",
        )
        if cumulative >= target:
            return int(bucket_ms)
    if _counter_value(counters, "partner_event_delivery_latency_bucket_gt_5000ms_total") > 0:
        return 5001
    return int(_PARTNER_EVENT_LATENCY_BUCKETS_MS[-1])


@dataclass(frozen=True)
class WsSliConfig:
    connection_accept_rate_target: float
    message_pass_rate_target: float
    sli_min_connection_attempts: int
    sli_min_messages: int
    burn_rate_windows_seconds: tuple[int, ...]
    burn_rate_fast_window_seconds: tuple[int, int]
    burn_rate_slow_window_seconds: tuple[int, int]
    burn_rate_fast_threshold: float
    burn_rate_slow_threshold: float
    burn_rate_min_connection_attempts: int
    burn_rate_min_messages: int


def build_ws_sli_payload(*, ws_snapshot: dict) -> dict:
    counters = ws_snapshot.get("counters", {}) if isinstance(ws_snapshot, dict) else {}
    if not isinstance(counters, dict):
        counters = {}

    accepted_connections = _counter_value(counters, "connections_accepted")
    rejected_connections = sum(
        _counter_value(counters, key)
        for key in (
            "connections_rejected_invalid_user_id",
            "connections_rejected_missing_token",
            "connections_rejected_invalid_token",
            "connections_rejected_user_not_found",
            "connections_rejected_rate_limited",
            "connections_rejected_global_cap",
            "connections_rejected_per_user_cap",
        )
    )
    total_connection_attempts = accepted_connections + rejected_connections

    messages_received = _counter_value(counters, "messages_received")
    messages_blocked = sum(
        _counter_value(counters, key)
        for key in (
            "messages_rate_limited",
            "messages_payload_too_large",
            "messages_backoff_active",
            "messages_blocked_other",
        )
    )
    messages_passed = max(0, messages_received - messages_blocked)

    partner_events_queued = _counter_value(counters, "partner_events_queued")
    partner_events_publish_attempted = _counter_value(counters, "partner_events_publish_attempted")
    partner_events_publish_succeeded = _counter_value(counters, "partner_events_publish_succeeded")
    partner_events_publish_failed = _counter_value(counters, "partner_events_publish_failed")
    partner_events_delivery_acked = _counter_value(counters, "partner_events_delivery_acked")
    partner_events_delivered = _counter_value(counters, "partner_events_delivered")
    partner_events_failed = _counter_value(counters, "partner_events_failed")
    partner_event_delivery_latency_p95_ms = _estimate_latency_p95_ms(counters=counters)

    return {
        "active_connections": ws_snapshot.get("active_connections", 0),
        "connection_attempts_total": total_connection_attempts,
        "connections_accepted_total": accepted_connections,
        "connections_rejected_total": rejected_connections,
        "connection_accept_rate": _safe_ratio(accepted_connections, total_connection_attempts),
        "messages_received_total": messages_received,
        "messages_blocked_total": messages_blocked,
        "messages_passed_total": messages_passed,
        "message_pass_rate": _safe_ratio(messages_passed, messages_received),
        "partner_events_queued_total": partner_events_queued,
        "partner_events_publish_attempted_total": partner_events_publish_attempted,
        "partner_events_publish_succeeded_total": partner_events_publish_succeeded,
        "partner_events_publish_failed_total": partner_events_publish_failed,
        "partner_event_publish_success_rate": _safe_ratio(
            partner_events_publish_succeeded,
            partner_events_publish_attempted,
        ),
        "partner_events_delivery_acked_total": partner_events_delivery_acked,
        "partner_events_delivered_total": partner_events_delivered,
        "partner_events_failed_total": partner_events_failed,
        "partner_event_delivery_ack_rate": _safe_ratio(
            partner_events_delivery_acked,
            partner_events_queued,
        ),
        "partner_event_arrival_rate": _safe_ratio(partner_events_delivered, partner_events_queued),
        "partner_event_delivery_latency_p95_ms": partner_event_delivery_latency_p95_ms,
    }


def build_ws_burn_rate_payload(*, ws_window_snapshots: dict[int, dict], config: WsSliConfig) -> dict:
    windows: list[dict] = []
    for window_seconds in config.burn_rate_windows_seconds:
        counters = ws_window_snapshots.get(window_seconds, {})
        if not isinstance(counters, dict):
            counters = {}

        accepted_connections = _counter_value(counters, "connections_accepted")
        rejected_connections = sum(
            _counter_value(counters, key)
            for key in (
                "connections_rejected_invalid_user_id",
                "connections_rejected_missing_token",
                "connections_rejected_invalid_token",
                "connections_rejected_user_not_found",
                "connections_rejected_rate_limited",
                "connections_rejected_global_cap",
                "connections_rejected_per_user_cap",
            )
        )
        total_connection_attempts = accepted_connections + rejected_connections

        messages_received = _counter_value(counters, "messages_received")
        messages_blocked = sum(
            _counter_value(counters, key)
            for key in (
                "messages_rate_limited",
                "messages_payload_too_large",
                "messages_backoff_active",
                "messages_blocked_other",
            )
        )

        windows.append(
            {
                "window_seconds": window_seconds,
                "window": _window_label(window_seconds),
                "connection_attempts_total": total_connection_attempts,
                "connections_rejected_total": rejected_connections,
                "connection_error_rate": _safe_ratio(rejected_connections, total_connection_attempts),
                "connection_burn_rate": _safe_burn_rate(
                    rejected_connections,
                    total_connection_attempts,
                    target_success_rate=config.connection_accept_rate_target,
                ),
                "enough_connection_samples": total_connection_attempts
                >= config.burn_rate_min_connection_attempts,
                "messages_received_total": messages_received,
                "messages_blocked_total": messages_blocked,
                "message_error_rate": _safe_ratio(messages_blocked, messages_received),
                "message_burn_rate": _safe_burn_rate(
                    messages_blocked,
                    messages_received,
                    target_success_rate=config.message_pass_rate_target,
                ),
                "enough_message_samples": messages_received >= config.burn_rate_min_messages,
            }
        )

    return {
        "windows": windows,
        "policy": {
            "fast_window_seconds": list(config.burn_rate_fast_window_seconds),
            "slow_window_seconds": list(config.burn_rate_slow_window_seconds),
            "fast_threshold": config.burn_rate_fast_threshold,
            "slow_threshold": config.burn_rate_slow_threshold,
            "min_connection_attempts": config.burn_rate_min_connection_attempts,
            "min_messages": config.burn_rate_min_messages,
        },
    }


def evaluate_ws_sli(*, ws_sli: dict, config: WsSliConfig) -> dict:
    connection_attempts_total = int(ws_sli.get("connection_attempts_total", 0) or 0)
    messages_received_total = int(ws_sli.get("messages_received_total", 0) or 0)
    connection_accept_rate = ws_sli.get("connection_accept_rate")
    message_pass_rate = ws_sli.get("message_pass_rate")

    reasons: list[str] = []
    evaluated = {
        "connection_attempts_total": connection_attempts_total,
        "messages_received_total": messages_received_total,
        "connection_attempts_threshold": config.sli_min_connection_attempts,
        "messages_received_threshold": config.sli_min_messages,
        "connection_accept_rate_target": config.connection_accept_rate_target,
        "message_pass_rate_target": config.message_pass_rate_target,
    }

    enough_connection_samples = connection_attempts_total >= config.sli_min_connection_attempts
    enough_message_samples = messages_received_total >= config.sli_min_messages
    evaluated["enough_connection_samples"] = enough_connection_samples
    evaluated["enough_message_samples"] = enough_message_samples

    if enough_connection_samples and isinstance(connection_accept_rate, (int, float)):
        if float(connection_accept_rate) < config.connection_accept_rate_target:
            reasons.append("ws_connection_accept_rate_below_target")

    if enough_message_samples and isinstance(message_pass_rate, (int, float)):
        if float(message_pass_rate) < config.message_pass_rate_target:
            reasons.append("ws_message_pass_rate_below_target")

    if reasons:
        return {
            "status": "degraded",
            "reasons": reasons,
            "evaluated": evaluated,
        }

    if not enough_connection_samples and not enough_message_samples:
        return {
            "status": "insufficient_data",
            "reasons": [],
            "evaluated": evaluated,
        }

    return {
        "status": "ok",
        "reasons": [],
        "evaluated": evaluated,
    }


def _evaluate_burn_pair(
    *,
    windows: dict[int, dict],
    pair_window_seconds: tuple[int, int],
    threshold: float,
    burn_rate_key: str,
    enough_samples_key: str,
) -> dict:
    pair_snapshots: list[dict] = []
    for window_seconds in pair_window_seconds:
        window_payload = windows.get(window_seconds) or {}
        enough_samples = bool(window_payload.get(enough_samples_key))
        burn_rate = window_payload.get(burn_rate_key)
        pair_snapshots.append(
            {
                "window_seconds": window_seconds,
                "window": _window_label(window_seconds),
                "enough_samples": enough_samples,
                "burn_rate": burn_rate if isinstance(burn_rate, (int, float)) else None,
            }
        )

    all_sampled = all(snapshot["enough_samples"] for snapshot in pair_snapshots)
    all_numeric = all(
        isinstance(snapshot.get("burn_rate"), (int, float))
        for snapshot in pair_snapshots
    )
    insufficient_data = not all_sampled or not all_numeric
    above_threshold = (
        all_sampled
        and all_numeric
        and all(float(snapshot["burn_rate"]) >= threshold for snapshot in pair_snapshots)
    )

    return {
        "threshold": threshold,
        "windows": pair_snapshots,
        "insufficient_data": insufficient_data,
        "above_threshold": above_threshold,
    }


def evaluate_ws_burn_rate(*, ws_burn_rate: dict, config: WsSliConfig) -> dict:
    windows_payload = ws_burn_rate.get("windows", []) if isinstance(ws_burn_rate, dict) else []
    windows_by_seconds: dict[int, dict] = {}
    if isinstance(windows_payload, list):
        for item in windows_payload:
            if not isinstance(item, dict):
                continue
            try:
                window_seconds = int(item.get("window_seconds", 0) or 0)
            except (TypeError, ValueError):
                continue
            if window_seconds > 0:
                windows_by_seconds[window_seconds] = item

    connection_fast = _evaluate_burn_pair(
        windows=windows_by_seconds,
        pair_window_seconds=config.burn_rate_fast_window_seconds,
        threshold=config.burn_rate_fast_threshold,
        burn_rate_key="connection_burn_rate",
        enough_samples_key="enough_connection_samples",
    )
    connection_slow = _evaluate_burn_pair(
        windows=windows_by_seconds,
        pair_window_seconds=config.burn_rate_slow_window_seconds,
        threshold=config.burn_rate_slow_threshold,
        burn_rate_key="connection_burn_rate",
        enough_samples_key="enough_connection_samples",
    )
    message_fast = _evaluate_burn_pair(
        windows=windows_by_seconds,
        pair_window_seconds=config.burn_rate_fast_window_seconds,
        threshold=config.burn_rate_fast_threshold,
        burn_rate_key="message_burn_rate",
        enough_samples_key="enough_message_samples",
    )
    message_slow = _evaluate_burn_pair(
        windows=windows_by_seconds,
        pair_window_seconds=config.burn_rate_slow_window_seconds,
        threshold=config.burn_rate_slow_threshold,
        burn_rate_key="message_burn_rate",
        enough_samples_key="enough_message_samples",
    )

    reasons: list[str] = []
    if connection_fast["above_threshold"]:
        reasons.append("ws_connection_burn_rate_fast_windows_above_threshold")
    if connection_slow["above_threshold"]:
        reasons.append("ws_connection_burn_rate_slow_windows_above_threshold")
    if message_fast["above_threshold"]:
        reasons.append("ws_message_burn_rate_fast_windows_above_threshold")
    if message_slow["above_threshold"]:
        reasons.append("ws_message_burn_rate_slow_windows_above_threshold")

    evaluated = {
        "connection_fast_pair": connection_fast,
        "connection_slow_pair": connection_slow,
        "message_fast_pair": message_fast,
        "message_slow_pair": message_slow,
    }

    if reasons:
        return {"status": "degraded", "reasons": reasons, "evaluated": evaluated}

    if (
        connection_fast["insufficient_data"]
        and connection_slow["insufficient_data"]
        and message_fast["insufficient_data"]
        and message_slow["insufficient_data"]
    ):
        return {"status": "insufficient_data", "reasons": [], "evaluated": evaluated}

    return {"status": "ok", "reasons": [], "evaluated": evaluated}
