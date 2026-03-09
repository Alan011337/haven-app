import uuid
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class CujEvent(SQLModel, table=True):
    __tablename__ = "cuj_events"
    __table_args__ = (
        Index("uq_cuj_events_dedupe_key", "dedupe_key", unique=True),
        Index("ix_cuj_events_user_event_created", "user_id", "event_name", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    occurred_at: Optional[datetime] = Field(default=None, nullable=True, index=True)

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
    mode: Optional[str] = Field(default=None, max_length=32, nullable=True, index=True)
    session_id: Optional[uuid.UUID] = Field(default=None, nullable=True, index=True)
    request_id: Optional[str] = Field(default=None, max_length=128, nullable=True, index=True)
    dedupe_key: str = Field(max_length=64, nullable=False)
    metadata_json: Optional[str] = Field(default=None, max_length=2000, nullable=True)
