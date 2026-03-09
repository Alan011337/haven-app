from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.cuj_event import CujEvent

logger = logging.getLogger(__name__)

DEFAULT_WINDOW_DAYS = 7
DEFAULT_MIN_EVENTS = 10
DEFAULT_MIN_PAIRS = 3
DEFAULT_TARGET_WRM_ACTIVE_PAIR_RATE = 0.2

WRM_DEFINITION_VERSION = "1.0.0"

WRM_ELIGIBLE_EVENT_NAMES: tuple[str, ...] = (
    "RITUAL_RESPOND",
    "RITUAL_UNLOCK",
    "JOURNAL_SUBMIT",
    "JOURNAL_ANALYSIS_DELIVERED",
)


@dataclass
class _PairAccumulator:
    participants: set[str] = field(default_factory=set)
    event_total: int = 0
    session_ids: set[str] = field(default_factory=set)


def _safe_int(value: Any, *, minimum: int = 0) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return minimum
    return parsed if parsed >= minimum else minimum


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(float(numerator) / float(denominator), 6)


def _normalize_pair_key(user_id: str, partner_user_id: str) -> str:
    lower = user_id.strip().lower()
    upper = partner_user_id.strip().lower()
    if lower <= upper:
        return f"{lower}:{upper}"
    return f"{upper}:{lower}"


def _pair_fingerprint(pair_key: str) -> str:
    return hashlib.sha256(pair_key.encode("utf-8")).hexdigest()[:12]


def build_growth_nsm_snapshot(
    *,
    session: Session,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> dict[str, Any]:
    safe_window_days = max(1, int(window_days))
    now = utcnow()
    window_started_at = now - timedelta(days=safe_window_days)

    query = (
        select(
            CujEvent.user_id,
            CujEvent.partner_user_id,
            CujEvent.event_name,
            CujEvent.session_id,
        )
        .where(
            CujEvent.created_at >= window_started_at,
            CujEvent.partner_user_id.is_not(None),
            CujEvent.event_name.in_(WRM_ELIGIBLE_EVENT_NAMES),
        )
    )
    rows = session.exec(query).all()

    pair_map: dict[str, _PairAccumulator] = {}
    events_by_name = {event_name: 0 for event_name in WRM_ELIGIBLE_EVENT_NAMES}
    ignored_rows = 0

    for row in rows:
        if isinstance(row, (tuple, list)):
            row_values = list(row)
        else:
            try:
                row_values = [row[0], row[1], row[2], row[3]]  # type: ignore[index]
            except Exception:
                logger.debug("growth_nsm_runtime row parse skip")
                ignored_rows += 1
                continue
        if len(row_values) < 4:
            ignored_rows += 1
            continue

        user_id = str(row_values[0] or "").strip().lower()
        partner_user_id = str(row_values[1] or "").strip().lower()
        event_name = str(row_values[2] or "").strip().upper()
        session_id = str(row_values[3]).strip() if row_values[3] else ""

        if not user_id or not partner_user_id or user_id == partner_user_id:
            ignored_rows += 1
            continue
        if event_name not in events_by_name:
            ignored_rows += 1
            continue

        pair_key = _normalize_pair_key(user_id, partner_user_id)
        pair_state = pair_map.setdefault(pair_key, _PairAccumulator())
        pair_state.participants.add(user_id)
        pair_state.event_total += 1
        if session_id:
            pair_state.session_ids.add(session_id)
        events_by_name[event_name] += 1

    qualifying_pairs = [state for state in pair_map.values() if len(state.participants) >= 2]
    qualifying_pair_fingerprints = sorted(
        _pair_fingerprint(pair_key)
        for pair_key, state in pair_map.items()
        if len(state.participants) >= 2
    )
    one_sided_pairs = [state for state in pair_map.values() if len(state.participants) < 2]

    qualifying_event_total = sum(state.event_total for state in qualifying_pairs)
    total_event_total = sum(state.event_total for state in pair_map.values())

    metrics = {
        "wrm_pairs_total": len(qualifying_pairs),
        "wrm_active_pair_rate": _safe_ratio(len(qualifying_pairs), len(pair_map)),
        "wrm_event_coverage_rate": _safe_ratio(qualifying_event_total, total_event_total),
    }

    return {
        "status": "ok",
        "definition_version": WRM_DEFINITION_VERSION,
        "window_days": safe_window_days,
        "window_started_at": f"{window_started_at.isoformat()}Z",
        "window_ended_at": f"{now.isoformat()}Z",
        "eligible_event_names": list(WRM_ELIGIBLE_EVENT_NAMES),
        "counts": {
            "active_pairs_observed_total": len(pair_map),
            "wrm_pairs_total": len(qualifying_pairs),
            "one_sided_pairs_total": len(one_sided_pairs),
            "eligible_events_total": total_event_total,
            "qualifying_events_total": qualifying_event_total,
            "ignored_rows_total": ignored_rows,
            "events_by_name": events_by_name,
        },
        "metrics": metrics,
        "samples": {
            "qualifying_pair_fingerprints": qualifying_pair_fingerprints[:10],
            "pair_observation_samples": min(10, len(pair_map)),
        },
        "targets": {
            "wrm_active_pair_rate": DEFAULT_TARGET_WRM_ACTIVE_PAIR_RATE,
        },
    }


def evaluate_growth_nsm_snapshot(
    snapshot: dict[str, Any],
    *,
    min_events: int = DEFAULT_MIN_EVENTS,
    min_pairs: int = DEFAULT_MIN_PAIRS,
    target_wrm_active_pair_rate: float = DEFAULT_TARGET_WRM_ACTIVE_PAIR_RATE,
) -> dict[str, Any]:
    status_value = str(snapshot.get("status") or "").strip().lower()
    if status_value != "ok":
        return {
            "status": "insufficient_data",
            "reasons": ["growth_nsm_snapshot_unavailable"],
            "evaluated": {
                "min_events": max(1, int(min_events)),
                "min_pairs": max(1, int(min_pairs)),
                "target_wrm_active_pair_rate": float(target_wrm_active_pair_rate),
            },
        }

    counts = snapshot.get("counts")
    metrics = snapshot.get("metrics")
    if not isinstance(counts, dict) or not isinstance(metrics, dict):
        return {
            "status": "insufficient_data",
            "reasons": ["growth_nsm_snapshot_shape_invalid"],
            "evaluated": {
                "min_events": max(1, int(min_events)),
                "min_pairs": max(1, int(min_pairs)),
                "target_wrm_active_pair_rate": float(target_wrm_active_pair_rate),
            },
        }

    safe_min_events = max(1, int(min_events))
    safe_min_pairs = max(1, int(min_pairs))
    safe_target_rate = max(0.0, min(1.0, float(target_wrm_active_pair_rate)))

    observed_events = _safe_int(counts.get("eligible_events_total"))
    observed_pairs = _safe_int(counts.get("active_pairs_observed_total"))
    wrm_pairs = _safe_int(counts.get("wrm_pairs_total"))
    wrm_active_pair_rate = _safe_float(metrics.get("wrm_active_pair_rate"))

    if observed_events < safe_min_events or observed_pairs < safe_min_pairs:
        return {
            "status": "insufficient_data",
            "reasons": [],
            "evaluated": {
                "min_events": safe_min_events,
                "min_pairs": safe_min_pairs,
                "target_wrm_active_pair_rate": safe_target_rate,
            },
            "meta": {
                "observed_events": observed_events,
                "observed_pairs": observed_pairs,
                "wrm_pairs": wrm_pairs,
                "wrm_active_pair_rate": wrm_active_pair_rate,
            },
        }

    reasons: list[str] = []
    if wrm_active_pair_rate is None:
        reasons.append("wrm_active_pair_rate_missing")
    elif wrm_active_pair_rate < safe_target_rate:
        reasons.append("wrm_active_pair_rate_below_target")

    return {
        "status": "pass" if not reasons else "degraded",
        "reasons": reasons,
        "evaluated": {
            "min_events": safe_min_events,
            "min_pairs": safe_min_pairs,
            "target_wrm_active_pair_rate": safe_target_rate,
        },
        "meta": {
            "observed_events": observed_events,
            "observed_pairs": observed_pairs,
            "wrm_pairs": wrm_pairs,
            "wrm_active_pair_rate": wrm_active_pair_rate,
        },
    }
