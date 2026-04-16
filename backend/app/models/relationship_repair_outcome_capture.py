import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipRepairOutcomeCapture(SQLModel, table=True):
    __tablename__ = "relationship_repair_outcome_captures"
    __table_args__ = (
        Index(
            "uq_relationship_repair_outcome_captures_session_id",
            "repair_session_id",
            unique=True,
        ),
        Index(
            "ix_relationship_repair_outcome_captures_pair_status",
            "user_id",
            "partner_id",
            "status",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    repair_session_id: str = Field(max_length=128, index=True)
    shared_commitment: str | None = Field(default=None, max_length=300)
    improvement_note: str | None = Field(default=None, max_length=300)
    status: str = Field(default="collecting", max_length=32, index=True)
    created_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    reviewed_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
    reviewed_at: datetime | None = Field(default=None, index=True)
