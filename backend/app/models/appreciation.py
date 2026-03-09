# Module B2: Appreciation Bank (gratitude notes to partner).

import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class Appreciation(SQLModel, table=True):
    __tablename__ = "appreciation"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # sender
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # recipient (the partner)
    body_text: str = Field(max_length=500)
    created_at: datetime = Field(default_factory=utcnow)
