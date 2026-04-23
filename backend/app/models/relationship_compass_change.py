import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipCompassChange(SQLModel, table=True):
    __tablename__ = "relationship_compass_changes"
    # `ix_rcc_` short prefix mirrors Heart's `ix_rrac_` — avoids Postgres's
    # 63-char identifier limit on compound index names.
    __table_args__ = (
        Index(
            "ix_rcc_pair_changed_at",
            "user_id",
            "partner_id",
            "changed_at",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    changed_at: datetime = Field(default_factory=utcnow, index=True)
    identity_statement_before: str | None = Field(default=None, max_length=500)
    identity_statement_after: str | None = Field(default=None, max_length=500)
    story_anchor_before: str | None = Field(default=None, max_length=500)
    story_anchor_after: str | None = Field(default=None, max_length=500)
    future_direction_before: str | None = Field(default=None, max_length=500)
    future_direction_after: str | None = Field(default=None, max_length=500)
    # Optional short human-authored note attached to this change event.
    # Never mandatory, never AI-generated. Rendered as a quiet italic excerpt
    # in the Compass timeline when present.
    revision_note: str | None = Field(default=None, max_length=300)
