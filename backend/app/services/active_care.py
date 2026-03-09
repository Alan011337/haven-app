# P2-D: Active Care — detect 3-day no interaction and send ice-breaker / draw invite.

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select, col, func

from app.core.datetime_utils import utcnow
from app.models.journal import Journal
from app.models.user import User
from app.models.card_response import CardResponse

logger = logging.getLogger(__name__)

ACTIVE_CARE_NO_INTERACTION_DAYS = 3


def get_last_pair_interaction_at(
    session: Session,
    user_id: UUID,
    partner_id: UUID,
) -> Optional[datetime]:
    """Last activity = max of (latest journal from either, latest card response from either)."""
    j = session.exec(
        select(func.max(Journal.created_at)).where(
            col(Journal.user_id).in_([user_id, partner_id]),
            Journal.deleted_at.is_(None),
        )
    ).one()
    cr = session.exec(
        select(func.max(CardResponse.created_at)).where(
            col(CardResponse.user_id).in_([user_id, partner_id]),
            CardResponse.deleted_at.is_(None),
        )
    ).one()
    candidates = [x for x in (j, cr) if x is not None]
    return max(candidates) if candidates else None


def _last_activity_by_user(
    session: Session, user_ids: list[UUID]
) -> tuple[dict[UUID, Optional[datetime]], dict[UUID, Optional[datetime]]]:
    """Return (last_journal_by_user_id, last_card_by_user_id) for batch N+1 avoidance."""
    if not user_ids:
        return {}, {}
    last_j = (
        session.exec(
            select(Journal.user_id, func.max(Journal.created_at)).where(
                col(Journal.user_id).in_(user_ids),
                Journal.deleted_at.is_(None),
            ).group_by(Journal.user_id)
        ).all()
    )
    last_cr = (
        session.exec(
            select(CardResponse.user_id, func.max(CardResponse.created_at)).where(
                col(CardResponse.user_id).in_(user_ids),
                CardResponse.deleted_at.is_(None),
            ).group_by(CardResponse.user_id)
        ).all()
    )
    journal_by_id = {uid: ts for uid, ts in last_j}
    card_by_id = {uid: ts for uid, ts in last_cr}
    return journal_by_id, card_by_id


def pairs_with_no_interaction_3_days(session: Session) -> list[tuple[User, User]]:
    """Return list of (user_a, user_b) where both are partnered and no interaction in 3 days."""
    cutoff = (utcnow() - timedelta(days=ACTIVE_CARE_NO_INTERACTION_DAYS)).replace(tzinfo=None)
    users_with_partner = list(
        session.exec(select(User).where(User.partner_id.isnot(None), User.deleted_at.is_(None)))
    )
    if not users_with_partner:
        return []

    # Batch load partners to avoid N+1
    partner_ids = [u.partner_id for u in users_with_partner if u.partner_id]
    partners = session.exec(select(User).where(col(User.id).in_(partner_ids))).all()
    partner_by_id = {p.id: p for p in partners}

    # Batch last activity per user (journal and card_response)
    all_user_ids = list({u.id for u in users_with_partner} | set(partner_ids))
    last_journal_by_id, last_card_by_id = _last_activity_by_user(session, all_user_ids)

    seen: set[tuple[UUID, UUID]] = set()
    out: list[tuple[User, User]] = []
    for user in users_with_partner:
        pid = user.partner_id
        if not pid:
            continue
        partner = partner_by_id.get(pid)
        if not partner or partner.partner_id != user.id:
            continue
        pair = (min(user.id, pid), max(user.id, pid))
        if pair in seen:
            continue
        seen.add(pair)
        # Per-pair last activity = max of both users' journal and card activity
        last_a_j = last_journal_by_id.get(user.id)
        last_a_c = last_card_by_id.get(user.id)
        last_b_j = last_journal_by_id.get(pid)
        last_b_c = last_card_by_id.get(pid)
        candidates = [x for x in (last_a_j, last_a_c, last_b_j, last_b_c) if x is not None]
        last = max(candidates) if candidates else None
        if last is not None and last >= cutoff:
            continue
        out.append((user, partner))
    return out
