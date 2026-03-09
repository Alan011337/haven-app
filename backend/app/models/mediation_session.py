# P2-D: Conflict mediation session (triggered by journal conflict-risk detection).

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow

if TYPE_CHECKING:
    pass


class MediationSession(SQLModel, table=True):
    __tablename__ = "mediation_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id_1: uuid.UUID = Field(foreign_key="users.id")
    user_id_2: uuid.UUID = Field(foreign_key="users.id")
    triggered_by_journal_id: uuid.UUID = Field(foreign_key="journals.id")
    created_at: datetime = Field(default_factory=utcnow)
    user_1_answered_at: Optional[datetime] = None
    user_2_answered_at: Optional[datetime] = None
