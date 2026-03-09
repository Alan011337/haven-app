from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class EventsLogDailyRollup(SQLModel, table=True):
    __tablename__ = "events_log_daily_rollups"
    __table_args__ = (
        Index(
            "uq_events_rollup_daily_event_source_scope",
            "rollup_date",
            "event_name",
            "source",
            "user_scope",
            unique=True,
        ),
        Index("ix_events_rollup_daily_date", "rollup_date"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    rollup_date: date = Field(nullable=False)
    event_name: str = Field(nullable=False, max_length=64)
    source: str = Field(nullable=False, max_length=64)
    user_scope: str = Field(nullable=False, max_length=32)
    event_count: int = Field(default=0, nullable=False)
