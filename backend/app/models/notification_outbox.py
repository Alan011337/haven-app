import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class NotificationOutboxStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    RETRY = "RETRY"
    SENT = "SENT"
    DEAD = "DEAD"


class NotificationOutbox(SQLModel, table=True):
    __tablename__ = "notification_outbox"
    __table_args__ = (
        Index("ix_notification_outbox_status_available_at", "status", "available_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    status: NotificationOutboxStatus = Field(default=NotificationOutboxStatus.PENDING, index=True)

    receiver_email: str = Field(nullable=False, index=True)
    sender_name: str = Field(nullable=False)
    action_type: str = Field(nullable=False, index=True)
    event_type: Optional[str] = Field(default=None, nullable=True, index=True)

    receiver_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    sender_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    source_session_id: Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)

    dedupe_key: Optional[str] = Field(default=None, nullable=True, index=True)
    dedupe_slot_reserved: bool = Field(default=False, nullable=False)

    attempt_count: int = Field(default=0, nullable=False)
    max_attempts: int = Field(default=3, nullable=False)
    available_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    last_attempt_at: Optional[datetime] = Field(default=None, nullable=True)
    last_error_reason: Optional[str] = Field(default=None, nullable=True)

    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False)
