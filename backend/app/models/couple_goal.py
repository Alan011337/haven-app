# Module A2: North star goal (one per couple).

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class CoupleGoal(SQLModel, table=True):
    __tablename__ = "couple_goal"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    goal_slug: str = Field(max_length=64, index=True)  # e.g. reduce_argument, increase_intimacy
    chosen_at: datetime = Field(default_factory=utcnow)
