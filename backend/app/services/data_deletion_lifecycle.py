from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlmodel import Session, col, or_, select

from app.core.datetime_utils import utcnow
from app.models.analysis import Analysis
from app.models.card_response import CardResponse
from app.models.card_session import CardSession
from app.models.journal import Journal
from app.models.notification_event import NotificationEvent
from app.models.user import User


@dataclass(frozen=True)
class SoftDeleteResult:
    deleted_at: datetime
    deleted_counts: dict[str, int]


def soft_delete_user_data(*, session: Session, current_user: User) -> SoftDeleteResult:
    user_id = current_user.id
    deleted_at = utcnow()

    if current_user.partner_id:
        partner = session.get(User, current_user.partner_id)
        if partner and partner.partner_id == user_id:
            partner.partner_id = None
            session.add(partner)

    journal_rows = session.exec(
        select(Journal).where(
            Journal.user_id == user_id,
            Journal.deleted_at.is_(None),
        )
    ).all()
    journal_ids = [row.id for row in journal_rows]

    analysis_rows: list[Analysis] = []
    if journal_ids:
        analysis_rows = session.exec(
            select(Analysis).where(
                col(Analysis.journal_id).in_(journal_ids),
                Analysis.deleted_at.is_(None),
            )
        ).all()

    session_rows = session.exec(
        select(CardSession).where(
            or_(
                CardSession.creator_id == user_id,
                CardSession.partner_id == user_id,
            ),
            CardSession.deleted_at.is_(None),
        )
    ).all()
    session_ids = [row.id for row in session_rows]

    response_filters: list[Any] = [CardResponse.user_id == user_id]
    if session_ids:
        response_filters.append(col(CardResponse.session_id).in_(session_ids))
    card_response_rows = session.exec(
        select(CardResponse).where(
            or_(*response_filters),
            CardResponse.deleted_at.is_(None),
        )
    ).all()

    notification_rows = session.exec(
        select(NotificationEvent).where(
            or_(
                NotificationEvent.receiver_user_id == user_id,
                NotificationEvent.sender_user_id == user_id,
            ),
            NotificationEvent.deleted_at.is_(None),
        )
    ).all()

    for row in analysis_rows:
        row.deleted_at = deleted_at
        session.add(row)
    for row in journal_rows:
        row.deleted_at = deleted_at
        session.add(row)
    for row in card_response_rows:
        row.deleted_at = deleted_at
        session.add(row)
    for row in session_rows:
        row.deleted_at = deleted_at
        session.add(row)
    for row in notification_rows:
        row.deleted_at = deleted_at
        session.add(row)

    current_user.deleted_at = deleted_at
    current_user.is_active = False
    current_user.partner_id = None
    current_user.invite_code = None
    current_user.invite_code_created_at = None
    session.add(current_user)

    deleted_counts: dict[str, int] = {
        "analyses": len(analysis_rows),
        "journals": len(journal_rows),
        "card_responses": len(card_response_rows),
        "card_sessions": len(session_rows),
        "notification_events": len(notification_rows),
        "users": 1,
    }
    return SoftDeleteResult(
        deleted_at=deleted_at,
        deleted_counts=deleted_counts,
    )
