# Module C1: SOS cool-down (time-out protocol).

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class CoolDownSession(SQLModel, table=True):
    __tablename__ = "cool_down_session"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # initiator
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    duration_minutes: int = Field(ge=20, le=60)
    starts_at: datetime = Field(default_factory=utcnow)
    ends_at: datetime = Field(index=True)
    state: str = Field(max_length=16, default="active", index=True)  # active | ended
