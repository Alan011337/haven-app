import logging
import uuid
from typing import Any, Optional

from sqlmodel import Session

from app.models.card_session import CardSession

logger = logging.getLogger(__name__)


def resolve_typing_session_id(
    *,
    session: Session,
    sender_user_id: uuid.UUID,
    partner_user_id: Optional[uuid.UUID],
    raw_session_id: Any,
) -> Optional[str]:
    """
    Validate session_id from websocket typing event.
    Only allows forwarding when sender and partner both belong to the same card session.
    """
    if partner_user_id is None:
        return None

    if raw_session_id is None:
        return None

    try:
        target_session_id = uuid.UUID(str(raw_session_id))
    except (ValueError, TypeError):
        logger.debug("Reject typing event: invalid_session_id_format")
        return None

    card_session = session.get(CardSession, target_session_id)
    if not card_session:
        logger.debug("Reject typing event: session_not_found")
        return None

    participants = {card_session.creator_id}
    if card_session.partner_id:
        participants.add(card_session.partner_id)

    if sender_user_id not in participants:
        logger.debug("Reject typing event: sender_not_participant")
        return None

    if partner_user_id not in participants:
        logger.debug("Reject typing event: partner_not_participant")
        return None

    return str(card_session.id)
