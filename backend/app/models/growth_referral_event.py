import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class GrowthReferralEventType(str, Enum):
    LANDING_VIEW = "LANDING_VIEW"
    SIGNUP = "SIGNUP"
    BIND = "BIND"
    COUPLE_INVITE = "COUPLE_INVITE"


class GrowthReferralEvent(SQLModel, table=True):
    __tablename__ = "growth_referral_events"
    __table_args__ = (
        Index("uq_growth_referral_events_dedupe_key", "dedupe_key", unique=True),
        Index(
            "ix_growth_referral_events_type_created_at",
            "event_type",
            "created_at",
        ),
        Index(
            "ix_growth_referral_events_inviter_created_at",
            "inviter_user_id",
            "created_at",
        ),
        Index(
            "ix_growth_referral_events_actor_created_at",
            "actor_user_id",
            "created_at",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    event_type: GrowthReferralEventType = Field(nullable=False, index=True)
    source: str = Field(default="UNKNOWN", max_length=64, nullable=False, index=True)
    invite_code_hash: str = Field(max_length=64, nullable=False, index=True)
    dedupe_key: str = Field(max_length=64, nullable=False)
    metadata_json: Optional[str] = Field(default=None, max_length=1024, nullable=True)

    inviter_user_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    actor_user_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
