import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class AuditEventOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    DENIED = "DENIED"
    ERROR = "ERROR"


class AuditEvent(SQLModel, table=True):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index(
            "ix_audit_events_actor_created_at",
            "actor_user_id",
            "created_at",
        ),
        Index(
            "ix_audit_events_action_created_at",
            "action",
            "created_at",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    actor_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    target_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)

    action: str = Field(nullable=False, max_length=100, index=True)
    resource_type: str = Field(nullable=False, max_length=64, index=True)
    resource_id: Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)

    outcome: AuditEventOutcome = Field(default=AuditEventOutcome.SUCCESS, nullable=False, index=True)
    reason: Optional[str] = Field(default=None, nullable=True, max_length=255)
    metadata_json: Optional[str] = Field(default=None, nullable=True, max_length=4000)

