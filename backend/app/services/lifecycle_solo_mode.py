"""LIFECYCLE-01: Solo mode lifecycle management.

When a user unbinds from their partner, the system transitions to solo mode:
- User data is preserved (journals, card responses)
- AI analysis switches to individual-focused prompts
- Partner-specific UI elements are hidden
- Data rights are maintained (no partner can access former data)
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlmodel import Session

from app.models.user import User

logger = logging.getLogger(__name__)

SOLO_MODE_FEATURES = {
    "ai_prompt_mode": "individual",
    "partner_ui_visible": False,
    "partner_data_accessible": False,
    "journal_visibility": "self_only",
    "card_mode": "individual",
    "notification_partner_events": False,
}


def resolve_user_mode(*, session: Session, user_id: UUID) -> dict[str, Any]:
    """Resolve whether a user is in solo or paired mode.

    Returns mode info dict with feature flags.
    """
    user = session.get(User, user_id)
    if not user:
        return {"mode": "unknown", "features": {}}

    if user.partner_id:
        # Check bidirectional validity
        partner = session.get(User, user.partner_id)
        if partner and partner.partner_id == user.id:
            return {
                "mode": "paired",
                "partner_id": str(user.partner_id),
                "features": {
                    "ai_prompt_mode": "couple",
                    "partner_ui_visible": True,
                    "partner_data_accessible": True,
                    "journal_visibility": "shared_analysis",
                    "card_mode": "couple",
                    "notification_partner_events": True,
                },
            }

    # Solo mode: either never paired or partner relationship is invalid
    return {
        "mode": "solo",
        "features": dict(SOLO_MODE_FEATURES),
    }


def transition_to_solo_mode(
    *,
    session: Session,
    user_id: UUID,
) -> dict[str, Any]:
    """Record the transition to solo mode after unbinding.

    Data is preserved. Only the mode context changes.
    """
    user = session.get(User, user_id)
    if not user:
        return {"status": "error", "reason": "user_not_found"}

    if user.partner_id:
        return {"status": "skipped", "reason": "user_still_paired"}

    logger.info("lifecycle_solo_mode_transition user_id=%s", user_id)
    return {
        "status": "ok",
        "mode": "solo",
        "features": dict(SOLO_MODE_FEATURES),
        "data_preserved": True,
    }
