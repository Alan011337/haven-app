import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"


class NotificationActionType(str, Enum):
    JOURNAL = "JOURNAL"
    CARD = "CARD"
    COOLDOWN_STARTED = "COOLDOWN_STARTED"
    MEDIATION_INVITE = "MEDIATION_INVITE"


class NotificationDeliveryStatus(str, Enum):
    QUEUED = "QUEUED"
    THROTTLED = "THROTTLED"
    SENT = "SENT"
    FAILED = "FAILED"


class NotificationEventBase(SQLModel):
    channel: NotificationChannel = Field(default=NotificationChannel.EMAIL, index=True)
    action_type: NotificationActionType = Field(index=True)
    status: NotificationDeliveryStatus = Field(index=True)

    receiver_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True, nullable=True)
    sender_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True, nullable=True)
    source_session_id: Optional[uuid.UUID] = Field(default=None, index=True, nullable=True)

    receiver_email: str = Field(index=True)
    dedupe_key: Optional[str] = Field(default=None, index=True, nullable=True)

    is_read: bool = Field(default=False, index=True)
    read_at: Optional[datetime] = Field(default=None, nullable=True)
    error_message: Optional[str] = Field(default=None, nullable=True)


class NotificationEvent(NotificationEventBase, table=True):
    __tablename__ = "notification_events"
    __table_args__ = (
        Index(
            "uq_notification_events_receiver_email_dedupe",
            "receiver_email",
            "dedupe_key",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)


class NotificationEventRead(NotificationEventBase):
    id: uuid.UUID
    created_at: datetime
