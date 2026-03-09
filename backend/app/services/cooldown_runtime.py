# Module C1: SOS cool-down runtime.

from __future__ import annotations

from datetime import timedelta
from typing import Optional
from uuid import UUID

from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.cool_down_session import CoolDownSession


def start_cooldown(
    session: Session,
    user_id: UUID,
    partner_id: UUID,
    duration_minutes: int,
) -> CoolDownSession:
    """Start a new cool-down session. Caller must validate 20 <= duration_minutes <= 60."""
    now = utcnow()
    ends_at = now + timedelta(minutes=duration_minutes)
    row = CoolDownSession(
        user_id=user_id,
        partner_id=partner_id,
        duration_minutes=duration_minutes,
        starts_at=now,
        ends_at=ends_at,
        state="active",
    )
    session.add(row)
    session.flush()
    return row


def get_active_cooldown(
    session: Session,
    user_id: UUID,
    partner_id: UUID,
) -> Optional[CoolDownSession]:
    """Return active cool-down for this pair (either direction), or None."""
    now = utcnow()
    row = session.exec(
        select(CoolDownSession).where(
            ((CoolDownSession.user_id == user_id) & (CoolDownSession.partner_id == partner_id))
            | ((CoolDownSession.user_id == partner_id) & (CoolDownSession.partner_id == user_id)),
            CoolDownSession.state == "active",
            CoolDownSession.ends_at > now,
        ).order_by(CoolDownSession.ends_at.desc()).limit(1)
    ).first()
    return row


def get_status_for_user(
    session: Session,
    current_user_id: UUID,
    partner_id: Optional[UUID],
) -> dict:
    """Return cooldown status for current user: in_cooldown, started_by_me, ends_at_iso, remaining_seconds."""
    if not partner_id:
        return {"in_cooldown": False, "started_by_me": False, "ends_at_iso": None, "remaining_seconds": None}
    active = get_active_cooldown(session, current_user_id, partner_id)
    if not active:
        return {"in_cooldown": False, "started_by_me": False, "ends_at_iso": None, "remaining_seconds": None}
    now = utcnow()
    remaining = max(0, int((active.ends_at - now).total_seconds()))
    return {
        "in_cooldown": True,
        "started_by_me": active.user_id == current_user_id,
        "ends_at_iso": active.ends_at.isoformat() + "Z",
        "remaining_seconds": remaining,
    }
