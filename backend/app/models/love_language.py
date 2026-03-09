# Module B3: Love Languages preference and weekly task.

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class LoveLanguagePreference(SQLModel, table=True):
    __tablename__ = "love_language_preference"

    user_id: uuid.UUID = Field(primary_key=True, foreign_key="users.id")
    # e.g. ["words", "acts", "gifts", "time", "touch"] or weights
    preference: dict = Field(sa_column=Column(JSON, nullable=False), default_factory=dict)
    updated_at: datetime = Field(default_factory=utcnow)


class LoveLanguageTaskAssignment(SQLModel, table=True):
    __tablename__ = "love_language_task_assignment"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    task_slug: str = Field(max_length=128, index=True)
    assigned_at: datetime = Field(default_factory=utcnow)
    completed_by_user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    completed_at: Optional[datetime] = None
