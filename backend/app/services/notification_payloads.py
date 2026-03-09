import uuid
from typing import Optional, TypedDict

from sqlmodel import Session

from app.models.user import User
from app.services.notification import NotificationDedupeEvent, build_notification_dedupe_key


class PartnerNotificationPayload(TypedDict):
    receiver_email: str
    sender_name: str
    dedupe_key: str
    receiver_user_id: uuid.UUID
    sender_user_id: uuid.UUID
    source_session_id: Optional[uuid.UUID]
    event_type: str  # trigger matrix key: journal_created, card_waiting, card_revealed


def build_partner_notification_payload(
    *,
    session: Session,
    sender_user: User,
    event_type: NotificationDedupeEvent,
    scope_id: uuid.UUID | str | None,
    source_session_id: Optional[uuid.UUID] = None,
    partner_user_id: Optional[uuid.UUID] = None,
) -> Optional[PartnerNotificationPayload]:
    """
    Build a normalized notification payload for partner email events.
    Supports event_type: journal, card_waiting, card_revealed, partner_bound.
    Returns None when partner context is not ready (no partner/email).
    """
    target_partner_id = partner_user_id or sender_user.partner_id
    if not target_partner_id:
        return None

    partner_user = session.get(User, target_partner_id)
    if not partner_user or not partner_user.email:
        return None

    if event_type == "journal":
        matrix_event = "journal_created"
    elif event_type == "partner_bound":
        matrix_event = "partner_bound"
    elif event_type == "time_capsule":
        matrix_event = "time_capsule"
    elif event_type == "active_care":
        matrix_event = "active_care"
    elif event_type == "mediation_invite":
        matrix_event = "mediation_invite"
    elif event_type == "cooldown_started":
        matrix_event = "cooldown_started"
    else:
        matrix_event = event_type
    return PartnerNotificationPayload(
        receiver_email=partner_user.email,
        sender_name=sender_user.full_name or "你的伴侶",
        dedupe_key=build_notification_dedupe_key(
            event_type=event_type,
            scope_id=scope_id,
            sender_user_id=sender_user.id,
            receiver_user_id=target_partner_id,
        ),
        receiver_user_id=partner_user.id,
        sender_user_id=sender_user.id,
        source_session_id=source_session_id,
        event_type=matrix_event,
    )
