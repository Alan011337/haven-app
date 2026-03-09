# Module B1: Daily 3-min sync (mood + daily question).

import uuid
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class DailySync(SQLModel, table=True):
    __tablename__ = "daily_sync"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    sync_date: date = Field(index=True)  # UTC date
    mood_score: int = Field(ge=1, le=5)
    question_id: str = Field(max_length=64)
    answer_text: str = Field(max_length=1000)
    created_at: datetime = Field(default_factory=utcnow)
