# P2-D / C3: Store mediation guided-question answers per user per session.

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class MediationAnswer(SQLModel, table=True):
    __tablename__ = "mediation_answers"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    mediation_session_id: uuid.UUID = Field(foreign_key="mediation_sessions.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    answer_1: str = Field(max_length=2000, default="")
    answer_2: str = Field(max_length=2000, default="")
    answer_3: str = Field(max_length=2000, default="")
    created_at: datetime = Field(default_factory=utcnow)
