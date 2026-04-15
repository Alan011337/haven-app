import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipCareProfile(SQLModel, table=True):
    __tablename__ = "relationship_care_profiles"
    __table_args__ = (
        Index(
            "uq_relationship_care_profiles_scope",
            "user_id",
            "partner_id",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    support_me: str | None = Field(default=None, max_length=500)
    avoid_when_stressed: str | None = Field(default=None, max_length=500)
    small_delights: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)
