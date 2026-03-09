import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class PushSubscriptionState(str, Enum):
    ACTIVE = "ACTIVE"
    INVALID = "INVALID"
    TOMBSTONED = "TOMBSTONED"
    PURGED = "PURGED"


class PushSubscription(SQLModel, table=True):
    __tablename__ = "push_subscriptions"
    __table_args__ = (
        Index("uq_push_subscriptions_endpoint", "endpoint", unique=True),
        Index("ix_push_subscriptions_user_state", "user_id", "state"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    last_success_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    last_failure_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    dry_run_sampled_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)

    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    endpoint: str = Field(max_length=2048, nullable=False)
    endpoint_hash: str = Field(max_length=64, nullable=False, index=True)
    p256dh_key: str = Field(max_length=512, nullable=False)
    auth_key: str = Field(max_length=512, nullable=False)
    user_agent: Optional[str] = Field(default=None, max_length=512, nullable=True)
    expiration_time: Optional[datetime] = Field(default=None, nullable=True)

    state: PushSubscriptionState = Field(default=PushSubscriptionState.ACTIVE, index=True)
    failure_count: int = Field(default=0, nullable=False)
    fail_reason: Optional[str] = Field(default=None, max_length=255, nullable=True)

