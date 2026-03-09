import uuid
from datetime import date, datetime
from enum import Enum

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class GamificationEventType(str, Enum):
    JOURNAL_CREATE = "JOURNAL_CREATE"


class GamificationScoreEvent(SQLModel, table=True):
    __tablename__ = "gamification_score_events"
    __table_args__ = (
        Index("uq_gamification_score_events_dedupe_key", "dedupe_key", unique=True),
        Index(
            "ix_gamification_score_events_user_event_date",
            "user_id",
            "event_date",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    journal_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("journals.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    event_type: GamificationEventType = Field(default=GamificationEventType.JOURNAL_CREATE, index=True)
    event_date: date = Field(nullable=False, index=True)
    content_hash: str = Field(max_length=64, nullable=False, index=True)
    dedupe_key: str = Field(max_length=64, nullable=False)
    score_delta: int = Field(default=0, nullable=False)
