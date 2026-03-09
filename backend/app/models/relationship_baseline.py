# Module A2: Relationship radar baseline (5 dimensions).

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Column, JSON
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipBaseline(SQLModel, table=True):
    __tablename__ = "relationship_baseline"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True, unique=True)  # one baseline per user
    partner_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", index=True)
    filled_at: datetime = Field(default_factory=utcnow)
    # 5 dimensions: intimacy, conflict, trust, communication, commitment (scores 1–5)
    scores: dict[str, Any] = Field(sa_column=Column(JSON, nullable=False), default_factory=dict)
