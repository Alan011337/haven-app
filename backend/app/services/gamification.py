from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.gamification_score_event import (
    GamificationEventType,
    GamificationScoreEvent,
)
from app.models.journal import Journal
from app.models.user import User
from app.models.user_streak_summary import UserStreakSummary

POSITIVE_MOOD_MARKERS = frozenset(
    {"happy", "calm", "grateful", "excited", "joy", "peaceful", "loved"}
)


@dataclass(frozen=True)
class ScoreApplyResult:
    applied_delta: int
    replay_blocked: bool
    dedupe_key: str


@dataclass(frozen=True)
class GamificationSummary:
    has_partner_context: bool
    streak_days: int
    best_streak_days: int
    streak_eligible_today: bool
    level: int
    level_points_total: int
    level_points_current: int
    level_points_target: int
    love_bar_percent: float
    level_title: str
    anti_cheat_enabled: bool


POINTS_PER_LEVEL = 100
LEVEL_TITLE_TABLE: tuple[tuple[int, str], ...] = (
    (1, "Warm Starter"),
    (3, "Daily Connector"),
    (6, "Heart Keeper"),
    (10, "Bond Architect"),
)


def _resolve_level_title(level: int) -> str:
    selected = LEVEL_TITLE_TABLE[0][1]
    for threshold, title in LEVEL_TITLE_TABLE:
        if level >= threshold:
            selected = title
        else:
            break
    return selected


def compute_journal_score_delta(ai_result: dict[str, Any]) -> int:
    safety = int(ai_result.get("safety_tier", 0) or 0)
    if safety > 0:
        return 0

    mood = str(ai_result.get("mood_label") or "").lower()
    if any(marker in mood for marker in POSITIVE_MOOD_MARKERS):
        return 10
    return 5


def _normalize_content(content: str) -> str:
    return " ".join((content or "").strip().split())


def _hash_content(content: str) -> str:
    normalized = _normalize_content(content).lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _build_dedupe_key(
    *,
    user_id: str,
    event_type: str,
    event_date_iso: str,
    content_hash: str,
) -> str:
    seed = f"{event_type}:{user_id}:{event_date_iso}:{content_hash}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def apply_journal_score_once(
    *,
    session: Session,
    current_user: User,
    journal_id: UUID,
    journal_content: str,
    event_at: datetime,
    candidate_delta: int,
) -> ScoreApplyResult:
    if candidate_delta <= 0:
        return ScoreApplyResult(applied_delta=0, replay_blocked=False, dedupe_key="")

    content_hash = _hash_content(journal_content)
    event_date = event_at.date()
    dedupe_key = _build_dedupe_key(
        user_id=str(current_user.id),
        event_type=GamificationEventType.JOURNAL_CREATE.value,
        event_date_iso=event_date.isoformat(),
        content_hash=content_hash,
    )

    existing = session.exec(
        select(GamificationScoreEvent.id).where(
            GamificationScoreEvent.dedupe_key == dedupe_key
        )
    ).first()
    if existing is not None:
        return ScoreApplyResult(applied_delta=0, replay_blocked=True, dedupe_key=dedupe_key)

    event_row = GamificationScoreEvent(
        user_id=current_user.id,
        journal_id=journal_id,
        event_type=GamificationEventType.JOURNAL_CREATE,
        event_date=event_date,
        content_hash=content_hash,
        dedupe_key=dedupe_key,
        score_delta=int(candidate_delta),
    )
    try:
        with session.begin_nested():
            session.add(event_row)
            session.flush()
    except IntegrityError:
        return ScoreApplyResult(applied_delta=0, replay_blocked=True, dedupe_key=dedupe_key)

    current_user.savings_score += int(candidate_delta)
    session.add(current_user)
    return ScoreApplyResult(
        applied_delta=int(candidate_delta),
        replay_blocked=False,
        dedupe_key=dedupe_key,
    )


def _extract_journal_dates(
    *,
    session: Session,
    user_id: UUID,
) -> set[date]:
    rows = session.exec(
        select(Journal.created_at).where(
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
    ).all()
    result: set[date] = set()
    for item in rows:
        if isinstance(item, datetime):
            result.add(item.date())
    return result


def _compute_consecutive_streak(*, shared_dates: set[date], today: date) -> int:
    streak = 0
    cursor = today
    while cursor in shared_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _compute_best_streak(shared_dates: set[date]) -> int:
    if not shared_dates:
        return 0
    ordered = sorted(shared_dates)
    best = 1
    current = 1
    for index in range(1, len(ordered)):
        if ordered[index] == ordered[index - 1] + timedelta(days=1):
            current += 1
        else:
            current = 1
        if current > best:
            best = current
    return best


def compute_gamification_summary(
    *,
    session: Session,
    current_user: User,
    partner_id: UUID | None,
) -> GamificationSummary:
    points_total = max(0, int(current_user.savings_score or 0))
    level = (points_total // POINTS_PER_LEVEL) + 1
    level_title = _resolve_level_title(level)
    points_current = points_total % POINTS_PER_LEVEL
    love_bar_percent = round((points_current / POINTS_PER_LEVEL) * 100, 1)
    today = utcnow().date()

    if not partner_id:
        return GamificationSummary(
            has_partner_context=False,
            streak_days=0,
            best_streak_days=0,
            streak_eligible_today=False,
            level=level,
            level_points_total=points_total,
            level_points_current=points_current,
            level_points_target=POINTS_PER_LEVEL,
            love_bar_percent=love_bar_percent,
            level_title=level_title,
            anti_cheat_enabled=True,
        )

    my_dates = _extract_journal_dates(session=session, user_id=current_user.id)
    partner_dates = _extract_journal_dates(session=session, user_id=partner_id)
    shared_dates = my_dates.intersection(partner_dates)

    return GamificationSummary(
        has_partner_context=True,
        streak_days=_compute_consecutive_streak(shared_dates=shared_dates, today=today),
        best_streak_days=_compute_best_streak(shared_dates),
        streak_eligible_today=today in shared_dates,
        level=level,
        level_points_total=points_total,
        level_points_current=points_current,
        level_points_target=POINTS_PER_LEVEL,
        love_bar_percent=love_bar_percent,
        level_title=level_title,
        anti_cheat_enabled=True,
    )


def get_or_compute_streak_summary(
    *,
    session: Session,
    current_user: User,
    partner_id: UUID | None,
) -> GamificationSummary:
    """
    DATA-READ-01: Return streak summary from precomputed table when fresh;
    otherwise compute, upsert, and return. TTL controlled by STREAK_SUMMARY_CACHE_TTL_SECONDS.
    """
    ttl_sec = max(0, getattr(settings, "STREAK_SUMMARY_CACHE_TTL_SECONDS", 300))
    now = utcnow()
    if ttl_sec > 0:
        row = session.get(UserStreakSummary, current_user.id)
        if row is not None:
            partner_match = (row.partner_id is None and partner_id is None) or (
                row.partner_id is not None and partner_id is not None and row.partner_id == partner_id
            )
            if partner_match:
                try:
                    age_sec = (now - row.updated_at).total_seconds()
                except (TypeError, AttributeError):
                    age_sec = float("inf")
                if age_sec < ttl_sec:
                    return GamificationSummary(
                        has_partner_context=row.has_partner_context,
                        streak_days=row.streak_days,
                        best_streak_days=row.best_streak_days,
                        streak_eligible_today=row.streak_eligible_today,
                        level=row.level,
                        level_points_total=row.level_points_total,
                        level_points_current=row.level_points_current,
                        level_points_target=row.level_points_target,
                        love_bar_percent=row.love_bar_percent,
                        level_title=row.level_title,
                        anti_cheat_enabled=row.anti_cheat_enabled,
                    )
    summary = compute_gamification_summary(
        session=session,
        current_user=current_user,
        partner_id=partner_id,
    )
    # Upsert precomputed row for next read
    row = session.get(UserStreakSummary, current_user.id)
    if row is None:
        row = UserStreakSummary(
            user_id=current_user.id,
            partner_id=partner_id,
            has_partner_context=summary.has_partner_context,
            streak_days=summary.streak_days,
            best_streak_days=summary.best_streak_days,
            streak_eligible_today=summary.streak_eligible_today,
            level=summary.level,
            level_points_total=summary.level_points_total,
            level_points_current=summary.level_points_current,
            level_points_target=summary.level_points_target,
            love_bar_percent=summary.love_bar_percent,
            level_title=summary.level_title,
            anti_cheat_enabled=summary.anti_cheat_enabled,
            updated_at=now,
        )
        session.add(row)
    else:
        row.partner_id = partner_id
        row.has_partner_context = summary.has_partner_context
        row.streak_days = summary.streak_days
        row.best_streak_days = summary.best_streak_days
        row.streak_eligible_today = summary.streak_eligible_today
        row.level = summary.level
        row.level_points_total = summary.level_points_total
        row.level_points_current = summary.level_points_current
        row.level_points_target = summary.level_points_target
        row.love_bar_percent = summary.love_bar_percent
        row.level_title = summary.level_title
        row.anti_cheat_enabled = summary.anti_cheat_enabled
        row.updated_at = now
        session.add(row)
    session.commit()
    return summary
