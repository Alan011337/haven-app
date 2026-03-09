"""CUJ/SLO metric runtime for Bind, Ritual, Journal, Unlock SLI aggregation.

Stable metric keys for event metadata (use these when emitting CUJ events):
- JOURNAL_PERSIST: CUJ_METRIC_JOURNAL_WRITE_MS
- JOURNAL_ANALYSIS_DELIVERED: CUJ_METRIC_ANALYSIS_LAG_MS
"""
from __future__ import annotations

import json
import logging
import math
from datetime import timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.cuj_event import CujEvent

logger = logging.getLogger(__name__)

# Canonical metric keys for CUJ event metadata (stable, use when emitting)
CUJ_METRIC_JOURNAL_WRITE_MS = "journal_write_ms"
CUJ_METRIC_ANALYSIS_LAG_MS = "analysis_async_lag_ms"
CUJ_METRIC_KEYS = {
    "journal_write": CUJ_METRIC_JOURNAL_WRITE_MS,
    "analysis_lag": CUJ_METRIC_ANALYSIS_LAG_MS,
}

EVENT_RITUAL_LOAD = "RITUAL_LOAD"
EVENT_RITUAL_DRAW = "RITUAL_DRAW"
EVENT_RITUAL_RESPOND = "RITUAL_RESPOND"
EVENT_RITUAL_UNLOCK = "RITUAL_UNLOCK"
EVENT_JOURNAL_SUBMIT = "JOURNAL_SUBMIT"
EVENT_JOURNAL_PERSIST = "JOURNAL_PERSIST"
EVENT_JOURNAL_ANALYSIS_QUEUED = "JOURNAL_ANALYSIS_QUEUED"
EVENT_JOURNAL_ANALYSIS_DELIVERED = "JOURNAL_ANALYSIS_DELIVERED"
EVENT_BIND_START = "BIND_START"
EVENT_BIND_SUCCESS = "BIND_SUCCESS"
EVENT_AI_FEEDBACK_DOWNVOTE = "AI_FEEDBACK_DOWNVOTE"

DEFAULT_WINDOW_HOURS = 24
DEFAULT_MIN_RATE_SAMPLES = 20
DEFAULT_MIN_LATENCY_SAMPLES = 10

CUJ_TARGETS: dict[str, float] = {
    "ritual_success_rate": 0.999,
    "journal_write_p95_ms": 4000.0,
    "analysis_async_lag_p95_ms": 4000.0,
    "partner_binding_success_rate": 0.999,
    "ai_feedback_downvote_rate_max": 0.05,
}

# Canonical key first; aliases for backward compatibility when reading
_JOURNAL_WRITE_LATENCY_KEYS: tuple[str, ...] = (
    CUJ_METRIC_JOURNAL_WRITE_MS,
    "write_latency_ms",
    "write_ms",
    "latency_ms",
)
_ANALYSIS_LAG_LATENCY_KEYS: tuple[str, ...] = (
    CUJ_METRIC_ANALYSIS_LAG_MS,
    "analysis_lag_ms",
    "lag_ms",
    "latency_ms",
)


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


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


def _extract_numeric_metadata_values(rows: list[Any], keys: tuple[str, ...]) -> list[float]:
    extracted: list[float] = []
    for row in rows:
        raw_json: str | None = None
        if isinstance(row, str):
            raw_json = row
        elif isinstance(row, (tuple, list)):
            raw_json = row[0] if row else None
        else:
            try:
                raw_json = row[0]  # type: ignore[index]
            except Exception:
                logger.debug("cuj_sli_runtime row json skip")
                raw_json = None
        if not raw_json:
            continue
        try:
            payload = json.loads(raw_json)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        for key in keys:
            value = payload.get(key)
            if isinstance(value, (int, float)):
                numeric_value = float(value)
                if numeric_value >= 0:
                    extracted.append(numeric_value)
                break
    return extracted


def _count_events_by_name(session: Session, *, window_started_at) -> dict[str, int]:
    query = (
        select(CujEvent.event_name, func.count())
        .where(CujEvent.created_at >= window_started_at)
        .group_by(CujEvent.event_name)
    )
    rows = session.exec(query).all()
    counts: dict[str, int] = {}
    for row in rows:
        event_name_raw: Any = None
        count_raw: Any = None
        if isinstance(row, (tuple, list)):
            if len(row) >= 2:
                event_name_raw = row[0]
                count_raw = row[1]
        else:
            try:
                event_name_raw = row[0]  # type: ignore[index]
                count_raw = row[1]  # type: ignore[index]
            except Exception:
                logger.debug("cuj_sli_runtime count row parse skip")
                continue
        event_name = str(event_name_raw or "").strip()
        if not event_name:
            continue
        counts[event_name] = _safe_int(count_raw)
    return counts


def _latency_rows_for_event_name(
    session: Session,
    *,
    window_started_at,
    event_name: str,
) -> list[Any]:
    query = (
        select(CujEvent.metadata_json)
        .where(
            CujEvent.created_at >= window_started_at,
            CujEvent.event_name == event_name,
            CujEvent.metadata_json.is_not(None),
        )
    )
    return session.exec(query).all()


def build_cuj_sli_snapshot(
    *,
    session: Session,
    window_hours: int = DEFAULT_WINDOW_HOURS,
) -> dict[str, Any]:
    safe_window_hours = max(1, int(window_hours))
    now = utcnow()
    window_started_at = now - timedelta(hours=safe_window_hours)

    counts = _count_events_by_name(session, window_started_at=window_started_at)
    counts_payload = {
        "ritual_load_total": counts.get(EVENT_RITUAL_LOAD, 0),
        "ritual_draw_total": counts.get(EVENT_RITUAL_DRAW, 0),
        "ritual_respond_total": counts.get(EVENT_RITUAL_RESPOND, 0),
        "ritual_unlock_total": counts.get(EVENT_RITUAL_UNLOCK, 0),
        "journal_submit_total": counts.get(EVENT_JOURNAL_SUBMIT, 0),
        "journal_persist_total": counts.get(EVENT_JOURNAL_PERSIST, 0),
        "journal_analysis_queued_total": counts.get(EVENT_JOURNAL_ANALYSIS_QUEUED, 0),
        "journal_analysis_delivered_total": counts.get(EVENT_JOURNAL_ANALYSIS_DELIVERED, 0),
        "bind_start_total": counts.get(EVENT_BIND_START, 0),
        "bind_success_total": counts.get(EVENT_BIND_SUCCESS, 0),
        "ai_feedback_downvote_total": counts.get(EVENT_AI_FEEDBACK_DOWNVOTE, 0),
    }

    journal_write_rows = _latency_rows_for_event_name(
        session,
        window_started_at=window_started_at,
        event_name=EVENT_JOURNAL_PERSIST,
    )
    analysis_lag_rows = _latency_rows_for_event_name(
        session,
        window_started_at=window_started_at,
        event_name=EVENT_JOURNAL_ANALYSIS_DELIVERED,
    )
    journal_write_latencies = _extract_numeric_metadata_values(
        journal_write_rows,
        _JOURNAL_WRITE_LATENCY_KEYS,
    )
    analysis_lag_latencies = _extract_numeric_metadata_values(
        analysis_lag_rows,
        _ANALYSIS_LAG_LATENCY_KEYS,
    )

    metrics_payload = {
        "ritual_success_rate": _safe_ratio(
            counts_payload["ritual_unlock_total"],
            counts_payload["ritual_draw_total"],
        ),
        "journal_persist_rate": _safe_ratio(
            counts_payload["journal_persist_total"],
            counts_payload["journal_submit_total"],
        ),
        "journal_analysis_delivery_rate": _safe_ratio(
            counts_payload["journal_analysis_delivered_total"],
            counts_payload["journal_analysis_queued_total"],
        ),
        "partner_binding_success_rate": _safe_ratio(
            counts_payload["bind_success_total"],
            counts_payload["bind_start_total"],
        ),
        "journal_write_p95_ms": _percentile(journal_write_latencies, 0.95),
        "analysis_async_lag_p95_ms": _percentile(analysis_lag_latencies, 0.95),
        "ai_feedback_downvote_rate": _safe_ratio(
            counts_payload["ai_feedback_downvote_total"],
            counts_payload["journal_analysis_delivered_total"],
        ),
    }

    return {
        "status": "ok",
        "window_hours": safe_window_hours,
        "window_started_at": f"{window_started_at.isoformat()}Z",
        "window_ended_at": f"{now.isoformat()}Z",
        "counts": counts_payload,
        "metrics": metrics_payload,
        "samples": {
            "journal_write_latency_samples": len(journal_write_latencies),
            "analysis_async_lag_samples": len(analysis_lag_latencies),
        },
        "targets": CUJ_TARGETS,
    }


def evaluate_cuj_sli_snapshot(
    snapshot: dict[str, Any],
    *,
    min_rate_samples: int = DEFAULT_MIN_RATE_SAMPLES,
    min_latency_samples: int = DEFAULT_MIN_LATENCY_SAMPLES,
) -> dict[str, Any]:
    status_value = str(snapshot.get("status") or "").strip().lower()
    if status_value != "ok":
        return {
            "status": "insufficient_data",
            "reasons": ["cuj_snapshot_unavailable"],
            "evaluated": {
                "min_rate_samples": min_rate_samples,
                "min_latency_samples": min_latency_samples,
            },
        }

    counts = snapshot.get("counts")
    metrics = snapshot.get("metrics")
    samples = snapshot.get("samples")
    if not isinstance(counts, dict) or not isinstance(metrics, dict) or not isinstance(samples, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["cuj_snapshot_shape_invalid"],
            "evaluated": {
                "min_rate_samples": min_rate_samples,
                "min_latency_samples": min_latency_samples,
            },
        }

    min_rates = max(1, int(min_rate_samples))
    min_latencies = max(1, int(min_latency_samples))

    ritual_denominator = _safe_int(counts.get("ritual_draw_total"))
    ritual_value = metrics.get("ritual_success_rate")
    binding_denominator = _safe_int(counts.get("bind_start_total"))
    binding_value = metrics.get("partner_binding_success_rate")
    journal_write_samples = _safe_int(samples.get("journal_write_latency_samples"))
    analysis_lag_samples = _safe_int(samples.get("analysis_async_lag_samples"))
    journal_write_p95 = metrics.get("journal_write_p95_ms")
    analysis_lag_p95 = metrics.get("analysis_async_lag_p95_ms")
    ai_downvote_rate = metrics.get("ai_feedback_downvote_rate")
    journal_analysis_delivered = _safe_int(counts.get("journal_analysis_delivered_total"))

    evaluated = {
        "min_rate_samples": min_rates,
        "min_latency_samples": min_latencies,
        "ritual_success_rate": {
            "value": ritual_value if isinstance(ritual_value, (int, float)) else None,
            "target": CUJ_TARGETS["ritual_success_rate"],
            "samples": ritual_denominator,
        },
        "partner_binding_success_rate": {
            "value": binding_value if isinstance(binding_value, (int, float)) else None,
            "target": CUJ_TARGETS["partner_binding_success_rate"],
            "samples": binding_denominator,
        },
        "journal_write_p95_ms": {
            "value": journal_write_p95 if isinstance(journal_write_p95, (int, float)) else None,
            "target": CUJ_TARGETS["journal_write_p95_ms"],
            "samples": journal_write_samples,
        },
        "analysis_async_lag_p95_ms": {
            "value": analysis_lag_p95 if isinstance(analysis_lag_p95, (int, float)) else None,
            "target": CUJ_TARGETS["analysis_async_lag_p95_ms"],
            "samples": analysis_lag_samples,
        },
        "ai_feedback_downvote_rate": {
            "value": ai_downvote_rate if isinstance(ai_downvote_rate, (int, float)) else None,
            "target": CUJ_TARGETS["ai_feedback_downvote_rate_max"],
            "samples": journal_analysis_delivered,
        },
    }

    degraded_reasons: list[str] = []
    insufficient = False

    if ritual_denominator < min_rates or not isinstance(ritual_value, (int, float)):
        insufficient = True
    elif float(ritual_value) < CUJ_TARGETS["ritual_success_rate"]:
        degraded_reasons.append("ritual_success_rate_below_target")

    if binding_denominator < min_rates or not isinstance(binding_value, (int, float)):
        insufficient = True
    elif float(binding_value) < CUJ_TARGETS["partner_binding_success_rate"]:
        degraded_reasons.append("partner_binding_success_rate_below_target")

    if journal_write_samples < min_latencies or not isinstance(journal_write_p95, (int, float)):
        insufficient = True
    elif float(journal_write_p95) > CUJ_TARGETS["journal_write_p95_ms"]:
        degraded_reasons.append("journal_write_p95_above_target")

    if analysis_lag_samples < min_latencies or not isinstance(analysis_lag_p95, (int, float)):
        insufficient = True
    elif float(analysis_lag_p95) > CUJ_TARGETS["analysis_async_lag_p95_ms"]:
        degraded_reasons.append("analysis_async_lag_p95_above_target")

    if journal_analysis_delivered >= min_rates and isinstance(ai_downvote_rate, (int, float)):
        if float(ai_downvote_rate) > CUJ_TARGETS["ai_feedback_downvote_rate_max"]:
            degraded_reasons.append("ai_feedback_downvote_rate_above_target")

    if degraded_reasons:
        return {
            "status": "degraded",
            "reasons": degraded_reasons,
            "evaluated": evaluated,
        }
    if insufficient:
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
