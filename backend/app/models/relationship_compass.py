import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipCompass(SQLModel, table=True):
    __tablename__ = "relationship_compasses"
    __table_args__ = (
        Index(
            "uq_relationship_compasses_scope",
            "user_id",
            "partner_id",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    identity_statement: str | None = Field(default=None, max_length=500)
    story_anchor: str | None = Field(default=None, max_length=500)
    future_direction: str | None = Field(default=None, max_length=500)
    updated_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
