# Module D1: Love Map — notes per layer (safe | medium | deep).

import uuid
from datetime import datetime
from enum import Enum

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class LoveMapLayer(str, Enum):
    SAFE = "safe"
    MEDIUM = "medium"
    DEEP = "deep"


class LoveMapNote(SQLModel, table=True):
    __tablename__ = "love_map_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    layer: str = Field(max_length=16, index=True)  # safe | medium | deep
    content: str = Field(max_length=5000, default="")
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
