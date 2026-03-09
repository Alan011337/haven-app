from __future__ import annotations

import hashlib
import json
import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import func
from sqlmodel import Session, col, select

from app.core.datetime_utils import utcnow
from app.middleware.request_context import request_id_var
from app.models.card_response import CardResponse
from app.models.cuj_event import CujEvent
from app.models.journal import Journal
from app.services.feature_flags import resolve_feature_flags

logger = logging.getLogger(__name__)

SYNC_NUDGE_EVENT_NAME = "SYNC_NUDGE_DELIVERED"
SYNC_NUDGE_REASON_COOLDOWN_ACTIVE = "cooldown_active"

DEFAULT_PARTNER_JOURNAL_WINDOW_HOURS = 24
DEFAULT_RITUAL_IDLE_WINDOW_HOURS = 72
DEFAULT_STREAK_RECOVERY_WINDOW_DAYS = 3
DEFAULT_NUDGE_COOLDOWN_HOURS = 18


@dataclass(frozen=True)
class SyncNudgeRecommendation:
    nudge_type: str
    title: str
    description: str
    eligible: bool
    reason: str
    dedupe_key: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SyncNudgeEvaluation:
    enabled: bool
    has_partner_context: bool
    kill_switch_active: bool
    nudge_cooldown_hours: int
    nudges: list[SyncNudgeRecommendation]


@dataclass(frozen=True)
class SyncNudgeDeliveryResult:
    accepted: bool
    deduped: bool
    nudge_type: str
    dedupe_key: str
    reason: str


def _safe_count(session: Session, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


def _iso_or_none(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return f"{value.isoformat()}Z"
    except AttributeError:
        return None


def _event_source(nudge_type: str) -> str:
    return f"sync_nudge:{nudge_type.strip().lower()}"


def _daily_bucket(now_value) -> str:
    return now_value.date().isoformat()


def _stable_daily_dedupe_key(
    *,
    user_id: uuid.UUID,
    partner_id: uuid.UUID,
    nudge_type: str,
    now_value,
) -> str:
    seed = f"{user_id}:{partner_id}:{nudge_type}:{_daily_bucket(now_value)}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _resolve_latest_journal_at(*, session: Session, user_id: uuid.UUID):
    return session.exec(
        select(func.max(Journal.created_at)).where(
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
    ).one()


def _resolve_latest_pair_card_response_at(
    *,
    session: Session,
    user_id: uuid.UUID,
    partner_id: uuid.UUID,
):
    return session.exec(
        select(func.max(CardResponse.created_at)).where(
            col(CardResponse.user_id).in_([user_id, partner_id]),
            CardResponse.deleted_at.is_(None),
        )
    ).one()


def _resolve_recent_journal_count(
    *,
    session: Session,
    user_id: uuid.UUID,
    from_time,
) -> int:
    statement = select(func.count(Journal.id)).where(
        Journal.user_id == user_id,
        Journal.deleted_at.is_(None),
        Journal.created_at >= from_time,
    )
    return _safe_count(session, statement)


def _resolve_recent_delivery_at(
    *,
    session: Session,
    user_id: uuid.UUID,
    nudge_type: str,
):
    return session.exec(
        select(func.max(CujEvent.created_at)).where(
            CujEvent.user_id == user_id,
            CujEvent.event_name == SYNC_NUDGE_EVENT_NAME,
            CujEvent.source == _event_source(nudge_type),
        )
    ).one()


def _apply_cooldown_if_needed(
    *,
    session: Session,
    user_id: uuid.UUID,
    nudge_type: str,
    now_value,
    eligible: bool,
    reason: str,
    metadata: dict[str, Any],
) -> tuple[bool, str, dict[str, Any]]:
    if not eligible:
        return eligible, reason, metadata

    latest_delivery_at = _resolve_recent_delivery_at(
        session=session,
        user_id=user_id,
        nudge_type=nudge_type,
    )
    metadata["latest_delivery_at"] = _iso_or_none(latest_delivery_at)
    metadata["cooldown_hours"] = DEFAULT_NUDGE_COOLDOWN_HOURS

    if latest_delivery_at and latest_delivery_at >= now_value - timedelta(hours=DEFAULT_NUDGE_COOLDOWN_HOURS):
        return False, SYNC_NUDGE_REASON_COOLDOWN_ACTIVE, metadata
    return eligible, reason, metadata


def _build_nudge(
    *,
    session: Session,
    now_value,
    user_id: uuid.UUID,
    partner_id: uuid.UUID,
    nudge_type: str,
    title: str,
    description: str,
    eligible: bool,
    reason: str,
    metadata: dict[str, Any],
) -> SyncNudgeRecommendation:
    adjusted_eligible, adjusted_reason, adjusted_metadata = _apply_cooldown_if_needed(
        session=session,
        user_id=user_id,
        nudge_type=nudge_type,
        now_value=now_value,
        eligible=eligible,
        reason=reason,
        metadata=metadata,
    )
    return SyncNudgeRecommendation(
        nudge_type=nudge_type,
        title=title,
        description=description,
        eligible=adjusted_eligible,
        reason=adjusted_reason,
        dedupe_key=_stable_daily_dedupe_key(
            user_id=user_id,
            partner_id=partner_id,
            nudge_type=nudge_type,
            now_value=now_value,
        ),
        metadata=adjusted_metadata,
    )


def evaluate_sync_nudges(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
) -> SyncNudgeEvaluation:
    has_partner_context = partner_user_id is not None
    resolved = resolve_feature_flags(has_partner=has_partner_context)
    kill_switch_active = bool(resolved.kill_switches.get("disable_growth_sync_nudges", False))
    feature_enabled = bool(resolved.flags.get("growth_sync_nudges_enabled", False))

    if not has_partner_context or kill_switch_active or not feature_enabled:
        growth_sync_nudge_runtime_metrics.record_evaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            eligible_count=0,
            cooldown_blocked_count=0,
        )
        return SyncNudgeEvaluation(
            enabled=False,
            has_partner_context=has_partner_context,
            kill_switch_active=kill_switch_active,
            nudge_cooldown_hours=DEFAULT_NUDGE_COOLDOWN_HOURS,
            nudges=[],
        )

    assert partner_user_id is not None
    now_value = utcnow()
    partner_latest_journal_at = _resolve_latest_journal_at(session=session, user_id=partner_user_id)
    user_latest_journal_at = _resolve_latest_journal_at(session=session, user_id=current_user_id)
    pair_latest_card_response_at = _resolve_latest_pair_card_response_at(
        session=session,
        user_id=current_user_id,
        partner_id=partner_user_id,
    )

    partner_journal_floor = now_value - timedelta(hours=DEFAULT_PARTNER_JOURNAL_WINDOW_HOURS)
    ritual_idle_floor = now_value - timedelta(hours=DEFAULT_RITUAL_IDLE_WINDOW_HOURS)
    streak_floor = now_value - timedelta(days=DEFAULT_STREAK_RECOVERY_WINDOW_DAYS)

    user_recent_journal_count = _resolve_recent_journal_count(
        session=session,
        user_id=current_user_id,
        from_time=streak_floor,
    )
    partner_recent_journal_count = _resolve_recent_journal_count(
        session=session,
        user_id=partner_user_id,
        from_time=streak_floor,
    )
    today_floor = now_value.replace(hour=0, minute=0, second=0, microsecond=0)
    user_today_count = _resolve_recent_journal_count(
        session=session,
        user_id=current_user_id,
        from_time=today_floor,
    )
    partner_today_count = _resolve_recent_journal_count(
        session=session,
        user_id=partner_user_id,
        from_time=today_floor,
    )
    pair_synced_today = user_today_count > 0 and partner_today_count > 0

    partner_journal_reply_eligible = False
    if partner_latest_journal_at is None:
        partner_journal_reply_reason = "partner_journal_missing"
    elif partner_latest_journal_at < partner_journal_floor:
        partner_journal_reply_reason = "partner_activity_not_recent"
    elif user_latest_journal_at and user_latest_journal_at >= partner_latest_journal_at:
        partner_journal_reply_reason = "already_synced"
    else:
        partner_journal_reply_eligible = True
        partner_journal_reply_reason = "eligible"

    ritual_resync_eligible = False
    if pair_latest_card_response_at is None:
        ritual_resync_eligible = True
        ritual_resync_reason = "pair_ritual_missing"
    elif pair_latest_card_response_at < ritual_idle_floor:
        ritual_resync_eligible = True
        ritual_resync_reason = "pair_ritual_idle_too_long"
    else:
        ritual_resync_reason = "pair_ritual_recently_active"

    streak_recovery_eligible = False
    if user_recent_journal_count < 1 or partner_recent_journal_count < 1:
        streak_recovery_reason = "pair_recent_history_missing"
    elif pair_synced_today:
        streak_recovery_reason = "already_synced_today"
    else:
        streak_recovery_eligible = True
        streak_recovery_reason = "eligible"

    nudges = [
        _build_nudge(
            session=session,
            now_value=now_value,
            user_id=current_user_id,
            partner_id=partner_user_id,
            nudge_type="PARTNER_JOURNAL_REPLY",
            title="伴侶剛剛寫了日記",
            description="回覆一段心情，幫雙方把今天的情緒對齊。",
            eligible=partner_journal_reply_eligible,
            reason=partner_journal_reply_reason,
            metadata={
                "partner_latest_journal_at": _iso_or_none(partner_latest_journal_at),
                "user_latest_journal_at": _iso_or_none(user_latest_journal_at),
                "fresh_window_hours": DEFAULT_PARTNER_JOURNAL_WINDOW_HOURS,
            },
        ),
        _build_nudge(
            session=session,
            now_value=now_value,
            user_id=current_user_id,
            partner_id=partner_user_id,
            nudge_type="RITUAL_RESYNC",
            title="今天來一張同步卡片",
            description="你們已經一段時間沒一起抽卡，現在是重新同步的好時機。",
            eligible=ritual_resync_eligible,
            reason=ritual_resync_reason,
            metadata={
                "pair_latest_card_response_at": _iso_or_none(pair_latest_card_response_at),
                "idle_window_hours": DEFAULT_RITUAL_IDLE_WINDOW_HOURS,
            },
        ),
        _build_nudge(
            session=session,
            now_value=now_value,
            user_id=current_user_id,
            partner_id=partner_user_id,
            nudge_type="STREAK_RECOVERY",
            title="把連勝拉回來",
            description="你們最近都有互動，今天只差一步就能維持共同節奏。",
            eligible=streak_recovery_eligible,
            reason=streak_recovery_reason,
            metadata={
                "user_recent_journal_count": user_recent_journal_count,
                "partner_recent_journal_count": partner_recent_journal_count,
                "pair_synced_today": pair_synced_today,
                "recovery_window_days": DEFAULT_STREAK_RECOVERY_WINDOW_DAYS,
            },
        ),
    ]

    eligible_count = sum(1 for item in nudges if item.eligible)
    cooldown_blocked_count = sum(1 for item in nudges if item.reason == SYNC_NUDGE_REASON_COOLDOWN_ACTIVE)
    growth_sync_nudge_runtime_metrics.record_evaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        eligible_count=eligible_count,
        cooldown_blocked_count=cooldown_blocked_count,
    )
    logger.info(
        "sync_nudges_evaluated enabled=true has_partner=%s eligible=%s cooldown_blocked=%s",
        has_partner_context,
        eligible_count,
        cooldown_blocked_count,
    )
    return SyncNudgeEvaluation(
        enabled=True,
        has_partner_context=has_partner_context,
        kill_switch_active=False,
        nudge_cooldown_hours=DEFAULT_NUDGE_COOLDOWN_HOURS,
        nudges=nudges,
    )


def deliver_sync_nudge(
    *,
    session: Session,
    current_user_id: uuid.UUID,
    partner_user_id: uuid.UUID | None,
    nudge_type: str,
    dedupe_key: str,
    source: str | None = None,
) -> SyncNudgeDeliveryResult:
    if partner_user_id is None:
        return SyncNudgeDeliveryResult(
            accepted=False,
            deduped=False,
            nudge_type=nudge_type,
            dedupe_key=dedupe_key,
            reason="partner_required",
        )

    now_value = utcnow()
    expected_dedupe_key = _stable_daily_dedupe_key(
        user_id=current_user_id,
        partner_id=partner_user_id,
        nudge_type=nudge_type,
        now_value=now_value,
    )
    if dedupe_key != expected_dedupe_key:
        return SyncNudgeDeliveryResult(
            accepted=False,
            deduped=False,
            nudge_type=nudge_type,
            dedupe_key=dedupe_key,
            reason="dedupe_key_mismatch",
        )

    existing_event = session.exec(
        select(CujEvent.id).where(CujEvent.dedupe_key == dedupe_key)
    ).first()
    if existing_event is not None:
        growth_sync_nudge_runtime_metrics.record_delivery(deduped=True)
        return SyncNudgeDeliveryResult(
            accepted=True,
            deduped=True,
            nudge_type=nudge_type,
            dedupe_key=dedupe_key,
            reason="deduped",
        )

    payload = {
        "nudge_type": nudge_type,
        "source": (source or "home"),
    }
    event = CujEvent(
        user_id=current_user_id,
        partner_user_id=partner_user_id,
        event_name=SYNC_NUDGE_EVENT_NAME,
        event_id=dedupe_key,
        source=_event_source(nudge_type),
        mode="BIND",
        session_id=None,
        request_id=request_id_var.get() or None,
        dedupe_key=dedupe_key,
        metadata_json=json.dumps(payload, ensure_ascii=True, sort_keys=True),
    )
    session.add(event)
    growth_sync_nudge_runtime_metrics.record_delivery(deduped=False)
    logger.info(
        "sync_nudge_delivered nudge_type=%s dedupe_key=%s source=%s",
        nudge_type,
        dedupe_key,
        payload["source"],
    )
    return SyncNudgeDeliveryResult(
        accepted=True,
        deduped=False,
        nudge_type=nudge_type,
        dedupe_key=dedupe_key,
        reason="accepted",
    )


class GrowthSyncNudgeRuntimeMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._counts: dict[str, int] = {}

    def _increment(self, key: str, value: int = 1) -> None:
        self._counts[key] = self._counts.get(key, 0) + value

    def record_evaluation(
        self,
        *,
        enabled: bool,
        has_partner_context: bool,
        eligible_count: int,
        cooldown_blocked_count: int,
    ) -> None:
        with self._lock:
            self._increment("growth_sync_nudge_evaluations_total")
            if enabled:
                self._increment("growth_sync_nudge_enabled_total")
            else:
                self._increment("growth_sync_nudge_disabled_total")
            if has_partner_context:
                self._increment("growth_sync_nudge_partner_context_total")
            if eligible_count > 0:
                self._increment("growth_sync_nudge_any_eligible_total")
            if cooldown_blocked_count > 0:
                self._increment("growth_sync_nudge_cooldown_blocked_total", cooldown_blocked_count)

    def record_delivery(self, *, deduped: bool) -> None:
        with self._lock:
            if deduped:
                self._increment("growth_sync_nudge_deliveries_deduped_total")
            else:
                self._increment("growth_sync_nudge_deliveries_total")

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


growth_sync_nudge_runtime_metrics = GrowthSyncNudgeRuntimeMetrics()
