import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class EventsLog(SQLModel, table=True):
    __tablename__ = "events_log"
    __table_args__ = (
        Index("uq_events_log_dedupe_key", "dedupe_key", unique=True),
        Index("ix_events_log_user_event_ts", "user_id", "event_name", "ts"),
        Index("ix_events_log_partner_event_ts", "partner_user_id", "event_name", "ts"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    ts: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    user_id: uuid.UUID = Field(
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    partner_user_id: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=sa.Column(
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )

    event_name: str = Field(max_length=64, nullable=False, index=True)
    event_id: str = Field(max_length=128, nullable=False, index=True)
    source: str = Field(default="web", max_length=64, nullable=False, index=True)
    session_id: Optional[str] = Field(default=None, max_length=128, nullable=True, index=True)
    device_id: Optional[str] = Field(default=None, max_length=128, nullable=True, index=True)

    props_json: Optional[str] = Field(default=None, max_length=2000, nullable=True)
    context_json: Optional[str] = Field(default=None, max_length=2000, nullable=True)
    privacy_json: Optional[str] = Field(default=None, max_length=2000, nullable=True)
    dedupe_key: str = Field(max_length=64, nullable=False)
