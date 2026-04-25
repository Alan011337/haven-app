import uuid
from datetime import date, datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipWeeklyReview(SQLModel, table=True):
    """
    Pair-scoped weekly reflection artifact for the Relationship System.

    Storage uses canonical user ordering (user1_id < user2_id) so there is a
    single row per pair/week regardless of which partner writes first.

    Each partner can update ONLY their own half via API authz rules; the other
    side is preserved verbatim.
    """

    __tablename__ = "relationship_weekly_reviews"
    __table_args__ = (
        Index(
            "uq_relationship_weekly_reviews_scope",
            "user1_id",
            "user2_id",
            "week_start",
            unique=True,
        ),
        Index(
            "ix_relationship_weekly_reviews_pair_week",
            "user1_id",
            "user2_id",
            "week_start",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user1_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    user2_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    week_start: date = Field(index=True)

    user1_understood: str | None = Field(default=None, max_length=2000)
    user1_worth: str | None = Field(default=None, max_length=2000)
    user1_needs_care: str | None = Field(default=None, max_length=2000)
    user1_next_week: str | None = Field(default=None, max_length=2000)
    user1_updated_at: datetime | None = Field(default=None)

    user2_understood: str | None = Field(default=None, max_length=2000)
    user2_worth: str | None = Field(default=None, max_length=2000)
    user2_needs_care: str | None = Field(default=None, max_length=2000)
    user2_next_week: str | None = Field(default=None, max_length=2000)
    user2_updated_at: datetime | None = Field(default=None)

    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow, index=True)

