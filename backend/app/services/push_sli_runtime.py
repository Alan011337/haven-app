from __future__ import annotations

import logging
import math
from datetime import timedelta
from threading import Lock
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.push_subscription import PushSubscription, PushSubscriptionState

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_HOURS = 24


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _safe_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return round(sorted_values[0], 3)

    rank = (len(sorted_values) - 1) * p
    low = int(math.floor(rank))
    high = int(math.ceil(rank))
    if low == high:
        return round(sorted_values[low], 3)

    low_value = sorted_values[low]
    high_value = sorted_values[high]
    return round(low_value + (high_value - low_value) * (rank - low), 3)


class PushRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = Lock()
        self._dispatch_success_total = 0
        self._dispatch_failure_total = 0
        self._dispatch_latencies_ms: list[float] = []
        self._dry_run_total = 0
        self._dry_run_sampled_total = 0
        self._dry_run_latencies_ms: list[float] = []
        self._subscription_upsert_total = 0
        self._subscription_created_total = 0
        self._subscription_delete_total = 0
        self._subscription_delete_noop_total = 0

    def _append_bounded_latency(self, latencies: list[float], value: float) -> None:
        latencies.append(value)
        if len(latencies) > 2000:
            del latencies[: len(latencies) - 2000]

    def record_dispatch(self, *, success: bool, latency_ms: float | None = None) -> None:
        with self._lock:
            if success:
                self._dispatch_success_total += 1
            else:
                self._dispatch_failure_total += 1
            if isinstance(latency_ms, (int, float)) and float(latency_ms) >= 0:
                self._append_bounded_latency(self._dispatch_latencies_ms, float(latency_ms))

    def record_dry_run(self, *, sampled_count: int, latency_ms: float | None = None) -> None:
        with self._lock:
            self._dry_run_total += 1
            self._dry_run_sampled_total += max(0, int(sampled_count))
            if isinstance(latency_ms, (int, float)) and float(latency_ms) >= 0:
                self._append_bounded_latency(self._dry_run_latencies_ms, float(latency_ms))

    def record_subscription_upsert(self, *, created: bool) -> None:
        with self._lock:
            self._subscription_upsert_total += 1
            if created:
                self._subscription_created_total += 1

    def record_subscription_delete(self, *, deleted: bool) -> None:
        with self._lock:
            if deleted:
                self._subscription_delete_total += 1
            else:
                self._subscription_delete_noop_total += 1

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            dispatch_latency_p95_ms = _percentile(self._dispatch_latencies_ms, 0.95)
            dry_run_latency_p95_ms = _percentile(self._dry_run_latencies_ms, 0.95)
            dispatch_attempts_total = self._dispatch_success_total + self._dispatch_failure_total
            return {
                "dispatch_attempts_total": dispatch_attempts_total,
                "dispatch_success_total": self._dispatch_success_total,
                "dispatch_failure_total": self._dispatch_failure_total,
                "dispatch_latency_p95_ms": dispatch_latency_p95_ms,
                "dry_run_total": self._dry_run_total,
                "dry_run_sampled_total": self._dry_run_sampled_total,
                "dry_run_latency_p95_ms": dry_run_latency_p95_ms,
                "subscription_upsert_total": self._subscription_upsert_total,
                "subscription_created_total": self._subscription_created_total,
                "subscription_delete_total": self._subscription_delete_total,
                "subscription_delete_noop_total": self._subscription_delete_noop_total,
            }

    def reset(self) -> None:
        with self._lock:
            self._dispatch_success_total = 0
            self._dispatch_failure_total = 0
            self._dispatch_latencies_ms.clear()
            self._dry_run_total = 0
            self._dry_run_sampled_total = 0
            self._dry_run_latencies_ms.clear()
            self._subscription_upsert_total = 0
            self._subscription_created_total = 0
            self._subscription_delete_total = 0
            self._subscription_delete_noop_total = 0


push_runtime_metrics = PushRuntimeMetrics()


def _coerce_push_state(value: object) -> PushSubscriptionState:
    if isinstance(value, PushSubscriptionState):
        return value
    try:
        return PushSubscriptionState(str(value))
    except Exception:
        return PushSubscriptionState.ACTIVE


def _build_state_counts(rows: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {
        "active": 0,
        "invalid": 0,
        "tombstoned": 0,
        "purged": 0,
    }
    for row in rows:
        state_raw = None
        count_raw = None
        if isinstance(row, (tuple, list)) and len(row) >= 2:
            state_raw = row[0]
            count_raw = row[1]
        else:
            try:
                state_raw = row[0]  # type: ignore[index]
                count_raw = row[1]  # type: ignore[index]
            except Exception:
                logger.debug("push_sli_runtime row parse skip")
                continue
        state_value = _coerce_push_state(state_raw)
        count_value = _safe_int(count_raw)
        if state_value == PushSubscriptionState.ACTIVE:
            counts["active"] += count_value
        elif state_value == PushSubscriptionState.INVALID:
            counts["invalid"] += count_value
        elif state_value == PushSubscriptionState.TOMBSTONED:
            counts["tombstoned"] += count_value
        elif state_value == PushSubscriptionState.PURGED:
            counts["purged"] += count_value
    return counts


def build_push_sli_snapshot(
    *,
    session: Session,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> dict[str, Any]:
    safe_window_hours = max(1, int(window_hours))
    now = utcnow()
    window_started_at = now - timedelta(hours=safe_window_hours)
    invalid_cutoff = now - timedelta(days=max(1, int(settings.PUSH_INVALID_RETENTION_DAYS)))
    tombstone_cutoff = now - timedelta(days=max(1, int(settings.PUSH_TOMBSTONE_PURGE_DAYS)))

    state_rows = session.exec(
        select(PushSubscription.state, func.count()).group_by(PushSubscription.state)
    ).all()
    state_counts = _build_state_counts(state_rows)

    stale_invalid_count = _safe_int(
        session.exec(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.state == PushSubscriptionState.INVALID,
                PushSubscription.updated_at < invalid_cutoff,
            )
        ).one()
        or 0
    )
    stale_tombstoned_count = _safe_int(
        session.exec(
            select(func.count(PushSubscription.id)).where(
                PushSubscription.state == PushSubscriptionState.TOMBSTONED,
                PushSubscription.updated_at < tombstone_cutoff,
            )
        ).one()
        or 0
    )

    runtime = push_runtime_metrics.snapshot()
    dispatch_attempts = _safe_int(runtime.get("dispatch_attempts_total"))
    dispatch_success = _safe_int(runtime.get("dispatch_success_total"))
    dispatch_failure = _safe_int(runtime.get("dispatch_failure_total"))
    dry_run_total = _safe_int(runtime.get("dry_run_total"))

    metrics = {
        "delivery_rate": _safe_ratio(dispatch_success, dispatch_attempts),
        "dispatch_latency_p95_ms": _safe_float(runtime.get("dispatch_latency_p95_ms")),
        "dry_run_latency_p95_ms": _safe_float(runtime.get("dry_run_latency_p95_ms")),
        "cleanup_stale_backlog_count": stale_invalid_count + stale_tombstoned_count,
    }

    return {
        "status": "ok",
        "window_hours": safe_window_hours,
        "window_started_at": f"{window_started_at.isoformat()}Z",
        "window_ended_at": f"{now.isoformat()}Z",
        "counts": {
            "active_subscriptions": state_counts["active"],
            "invalid_subscriptions": state_counts["invalid"],
            "tombstoned_subscriptions": state_counts["tombstoned"],
            "purged_subscriptions": state_counts["purged"],
            "stale_invalid_subscriptions": stale_invalid_count,
            "stale_tombstoned_subscriptions": stale_tombstoned_count,
            "dispatch_attempts_total": dispatch_attempts,
            "dispatch_success_total": dispatch_success,
            "dispatch_failure_total": dispatch_failure,
            "dry_run_total": dry_run_total,
            "dry_run_sampled_total": _safe_int(runtime.get("dry_run_sampled_total")),
            "subscription_upsert_total": _safe_int(runtime.get("subscription_upsert_total")),
            "subscription_created_total": _safe_int(runtime.get("subscription_created_total")),
            "subscription_delete_total": _safe_int(runtime.get("subscription_delete_total")),
            "subscription_delete_noop_total": _safe_int(runtime.get("subscription_delete_noop_total")),
        },
        "metrics": metrics,
        "samples": {
            "dispatch_attempts": dispatch_attempts,
            "dry_run_samples": dry_run_total,
        },
        "targets": {
            "delivery_rate": float(settings.HEALTH_PUSH_DELIVERY_RATE_TARGET),
            "dispatch_latency_p95_ms": float(settings.HEALTH_PUSH_DISPATCH_P95_MS_TARGET),
            "dry_run_latency_p95_ms": float(settings.HEALTH_PUSH_DRY_RUN_P95_MS_TARGET),
            "cleanup_stale_backlog_max": int(settings.HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX),
        },
    }


def evaluate_push_sli_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    status_value = str(snapshot.get("status") or "").strip().lower()
    if status_value != "ok":
        return {
            "status": "insufficient_data",
            "reasons": ["push_snapshot_unavailable"],
            "evaluated": {},
        }

    counts = snapshot.get("counts")
    metrics = snapshot.get("metrics")
    samples = snapshot.get("samples")
    targets = snapshot.get("targets")
    if not isinstance(counts, dict) or not isinstance(metrics, dict) or not isinstance(samples, dict) or not isinstance(targets, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["push_snapshot_shape_invalid"],
            "evaluated": {},
        }

    min_dispatch_samples = max(1, int(settings.HEALTH_PUSH_SLI_MIN_DISPATCH_ATTEMPTS))
    min_dry_run_samples = max(1, int(settings.HEALTH_PUSH_SLI_MIN_DRY_RUN_SAMPLES))
    target_delivery_rate = float(settings.HEALTH_PUSH_DELIVERY_RATE_TARGET)
    target_dispatch_p95_ms = float(settings.HEALTH_PUSH_DISPATCH_P95_MS_TARGET)
    target_dry_run_p95_ms = float(settings.HEALTH_PUSH_DRY_RUN_P95_MS_TARGET)
    target_cleanup_backlog_max = max(0, int(settings.HEALTH_PUSH_STALE_CLEANUP_BACKLOG_MAX))

    dispatch_attempts = _safe_int(samples.get("dispatch_attempts"))
    dry_run_samples = _safe_int(samples.get("dry_run_samples"))
    delivery_rate = _safe_float(metrics.get("delivery_rate"))
    dispatch_latency_p95 = _safe_float(metrics.get("dispatch_latency_p95_ms"))
    dry_run_latency_p95 = _safe_float(metrics.get("dry_run_latency_p95_ms"))
    cleanup_backlog = _safe_int(metrics.get("cleanup_stale_backlog_count"))

    evaluated = {
        "delivery_rate": {
            "value": delivery_rate,
            "target": target_delivery_rate,
            "samples": dispatch_attempts,
            "min_samples": min_dispatch_samples,
        },
        "dispatch_latency_p95_ms": {
            "value": dispatch_latency_p95,
            "target": target_dispatch_p95_ms,
            "samples": dispatch_attempts,
            "min_samples": min_dispatch_samples,
        },
        "dry_run_latency_p95_ms": {
            "value": dry_run_latency_p95,
            "target": target_dry_run_p95_ms,
            "samples": dry_run_samples,
            "min_samples": min_dry_run_samples,
        },
        "cleanup_stale_backlog_count": {
            "value": cleanup_backlog,
            "target": target_cleanup_backlog_max,
        },
    }

    degraded_reasons: list[str] = []
    insufficient_data = False

    if dispatch_attempts < min_dispatch_samples or delivery_rate is None:
        insufficient_data = True
    elif delivery_rate < target_delivery_rate:
        degraded_reasons.append("push_delivery_rate_below_target")

    if dispatch_attempts < min_dispatch_samples or dispatch_latency_p95 is None:
        insufficient_data = True
    elif dispatch_latency_p95 > target_dispatch_p95_ms:
        degraded_reasons.append("push_dispatch_latency_p95_above_target")

    if dry_run_samples < min_dry_run_samples or dry_run_latency_p95 is None:
        insufficient_data = True
    elif dry_run_latency_p95 > target_dry_run_p95_ms:
        degraded_reasons.append("push_dry_run_latency_p95_above_target")

    if cleanup_backlog > target_cleanup_backlog_max:
        degraded_reasons.append("push_cleanup_backlog_above_target")

    if degraded_reasons:
        return {"status": "degraded", "reasons": degraded_reasons, "evaluated": evaluated}
    if insufficient_data:
        return {"status": "insufficient_data", "reasons": [], "evaluated": evaluated}
    return {"status": "ok", "reasons": [], "evaluated": evaluated}
