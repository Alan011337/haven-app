# Module D2: Date suggestions — "兩週無活動" logic.

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, func, or_, and_

from app.models.journal import Journal
from app.models.card_response import CardResponse
from app.models.card_session import CardSession

NO_ACTIVITY_DAYS = 14

# 約會提案靜態清單（計畫：可預設一組靜態清單）
DATE_IDEAS_STATIC = [
    "今晚在家盲測品酒",
    "一起做一道沒做過的菜",
    "散步 30 分鐘不滑手機",
    "選一部兩人都想看的電影",
    "週末去一間沒去過的咖啡廳",
    "一起寫下三件感謝對方的事",
    "在家燭光晚餐",
]


def get_last_pair_activity_at(
    session: Session,
    user_id: UUID,
    partner_id: UUID,
) -> Optional[datetime]:
    """Return the most recent activity (journal or card response in shared session) for the pair."""
    uid1, uid2 = min(user_id, partner_id), max(user_id, partner_id)

    # Last journal by either user
    journal_row = session.exec(
        select(func.max(Journal.created_at)).where(
            or_(Journal.user_id == uid1, Journal.user_id == uid2),
            Journal.deleted_at.is_(None),
        )
    ).first()
    last_journal = journal_row if isinstance(journal_row, datetime) else None

    # Last card response in a session that belongs to this pair
    card_row = session.exec(
        select(func.max(CardResponse.created_at))
        .select_from(CardResponse)
        .join(CardSession, CardResponse.session_id == CardSession.id)
        .where(
            CardResponse.deleted_at.is_(None),
            CardSession.deleted_at.is_(None),
            or_(
                and_(CardSession.creator_id == uid1, CardSession.partner_id == uid2),
                and_(CardSession.creator_id == uid2, CardSession.partner_id == uid1),
            ),
        )
    ).first()
    last_card = card_row if isinstance(card_row, datetime) else None

    candidates = [t for t in (last_journal, last_card) if t is not None]
    return max(candidates) if candidates else None


def get_date_suggestion(
    session: Session,
    user_id: UUID,
    partner_id: Optional[UUID],
) -> dict:
    """Return suggested: bool, message, last_activity_at (iso), suggestions (static list when suggested)."""
    if not partner_id:
        return {"suggested": False, "message": "", "last_activity_at": None, "suggestions": []}
    last = get_last_pair_activity_at(session, user_id, partner_id)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=NO_ACTIVITY_DAYS)
    if last is None or last.replace(tzinfo=timezone.utc) < cutoff:
        return {
            "suggested": True,
            "message": "好久沒一起互動了，來場小約會吧！",
            "last_activity_at": last.isoformat() + "Z" if last else None,
            "suggestions": list(DATE_IDEAS_STATIC),
        }
    return {
        "suggested": False,
        "message": "",
        "last_activity_at": last.isoformat() + "Z" if last else None,
        "suggestions": [],
    }
