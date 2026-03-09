from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import update as sqlalchemy_update
from sqlmodel import Session, col, or_, select

from app.core.datetime_utils import utcnow
from app.models.analysis import Analysis
from app.models.audit_event import AuditEvent
from app.models.card_response import CardResponse
from app.models.card_session import CardSession
from app.models.journal import Journal
from app.models.notification_event import NotificationEvent
from app.models.user import User

SOFT_DELETE_PURGE_COUNT_KEYS: tuple[str, ...] = (
    "analyses",
    "journals",
    "card_responses",
    "card_sessions",
    "notification_events",
    "users",
)


@dataclass(frozen=True)
class SoftDeletePurgeResult:
    cutoff: datetime
    dry_run: bool
    candidate_counts: dict[str, int]
    purged_counts: dict[str, int]


def purge_soft_deleted_rows(
    *,
    session: Session,
    purge_retention_days: int,
    dry_run: bool,
    now: datetime | None = None,
) -> SoftDeletePurgeResult:
    effective_retention_days = max(1, int(purge_retention_days))
    cutoff = (now or utcnow()) - timedelta(days=effective_retention_days)

    analysis_rows = session.exec(
        select(Analysis).where(
            Analysis.deleted_at.is_not(None),
            Analysis.deleted_at <= cutoff,
        )
    ).all()
    journal_rows = session.exec(
        select(Journal).where(
            Journal.deleted_at.is_not(None),
            Journal.deleted_at <= cutoff,
        )
    ).all()
    card_response_rows = session.exec(
        select(CardResponse).where(
            CardResponse.deleted_at.is_not(None),
            CardResponse.deleted_at <= cutoff,
        )
    ).all()
    card_session_rows = session.exec(
        select(CardSession).where(
            CardSession.deleted_at.is_not(None),
            CardSession.deleted_at <= cutoff,
        )
    ).all()
    notification_rows = session.exec(
        select(NotificationEvent).where(
            NotificationEvent.deleted_at.is_not(None),
            NotificationEvent.deleted_at <= cutoff,
        )
    ).all()
    user_rows = session.exec(
        select(User).where(
            User.deleted_at.is_not(None),
            User.deleted_at <= cutoff,
        )
    ).all()
    purge_eligible_user_rows = list(user_rows)
    if user_rows:
        candidate_user_ids = [row.id for row in user_rows]
        blocked_user_ids: set = set()

        blocked_user_ids.update(
            user_id
            for user_id in session.exec(
                select(Journal.user_id).where(
                    col(Journal.user_id).in_(candidate_user_ids),
                    or_(
                        Journal.deleted_at.is_(None),
                        Journal.deleted_at > cutoff,
                    ),
                )
            ).all()
            if user_id is not None
        )
        blocked_user_ids.update(
            user_id
            for user_id in session.exec(
                select(CardResponse.user_id).where(
                    col(CardResponse.user_id).in_(candidate_user_ids),
                    or_(
                        CardResponse.deleted_at.is_(None),
                        CardResponse.deleted_at > cutoff,
                    ),
                )
            ).all()
            if user_id is not None
        )

        blocked_session_creator_ids = session.exec(
            select(CardSession.creator_id).where(
                col(CardSession.creator_id).in_(candidate_user_ids),
                or_(
                    CardSession.deleted_at.is_(None),
                    CardSession.deleted_at > cutoff,
                ),
            )
        ).all()
        blocked_session_partner_ids = session.exec(
            select(CardSession.partner_id).where(
                col(CardSession.partner_id).in_(candidate_user_ids),
                or_(
                    CardSession.deleted_at.is_(None),
                    CardSession.deleted_at > cutoff,
                ),
            )
        ).all()
        blocked_user_ids.update(
            user_id
            for user_id in blocked_session_creator_ids
            if user_id is not None
        )
        blocked_user_ids.update(
            user_id
            for user_id in blocked_session_partner_ids
            if user_id is not None
        )

        blocked_receiver_ids = session.exec(
            select(NotificationEvent.receiver_user_id).where(
                col(NotificationEvent.receiver_user_id).in_(candidate_user_ids),
                or_(
                    NotificationEvent.deleted_at.is_(None),
                    NotificationEvent.deleted_at > cutoff,
                ),
            )
        ).all()
        blocked_sender_ids = session.exec(
            select(NotificationEvent.sender_user_id).where(
                col(NotificationEvent.sender_user_id).in_(candidate_user_ids),
                or_(
                    NotificationEvent.deleted_at.is_(None),
                    NotificationEvent.deleted_at > cutoff,
                ),
            )
        ).all()
        blocked_user_ids.update(
            user_id
            for user_id in blocked_receiver_ids
            if user_id is not None
        )
        blocked_user_ids.update(
            user_id
            for user_id in blocked_sender_ids
            if user_id is not None
        )

        purge_eligible_user_rows = [
            row for row in user_rows if row.id not in blocked_user_ids
        ]

    candidate_counts: dict[str, int] = {
        "analyses": len(analysis_rows),
        "journals": len(journal_rows),
        "card_responses": len(card_response_rows),
        "card_sessions": len(card_session_rows),
        "notification_events": len(notification_rows),
        "users": len(purge_eligible_user_rows),
    }

    purged_counts = {key: 0 for key in SOFT_DELETE_PURGE_COUNT_KEYS}
    if dry_run:
        return SoftDeletePurgeResult(
            cutoff=cutoff,
            dry_run=True,
            candidate_counts=candidate_counts,
            purged_counts=purged_counts,
        )

    user_ids = [row.id for row in purge_eligible_user_rows]
    if user_ids:
        session.exec(
            sqlalchemy_update(AuditEvent)
            .where(col(AuditEvent.actor_user_id).in_(user_ids))
            .values(actor_user_id=None)
        )
        session.exec(
            sqlalchemy_update(AuditEvent)
            .where(col(AuditEvent.target_user_id).in_(user_ids))
            .values(target_user_id=None)
        )

    for row in analysis_rows:
        session.delete(row)
    for row in journal_rows:
        session.delete(row)
    for row in card_response_rows:
        session.delete(row)
    for row in card_session_rows:
        session.delete(row)
    for row in notification_rows:
        session.delete(row)
    for row in purge_eligible_user_rows:
        session.delete(row)

    purged_counts = dict(candidate_counts)
    return SoftDeletePurgeResult(
        cutoff=cutoff,
        dry_run=False,
        candidate_counts=candidate_counts,
        purged_counts=purged_counts,
    )
