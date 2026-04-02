import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Column, Index, JSON
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipKnowledgeSuggestion(SQLModel, table=True):
    __tablename__ = "relationship_knowledge_suggestions"
    __table_args__ = (
        Index(
            "ix_rel_knowledge_suggestions_scope_status",
            "user_id",
            "partner_id",
            "section",
            "status",
        ),
        Index(
            "uq_rel_knowledge_suggestions_scope_dedupe",
            "user_id",
            "partner_id",
            "section",
            "dedupe_key",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    section: str = Field(default="shared_future", max_length=64, index=True)
    status: str = Field(default="pending", max_length=32, index=True)
    generator_version: str = Field(default="shared_future_v1", max_length=64)
    proposed_title: str = Field(max_length=500)
    proposed_notes: str = Field(default="", max_length=2000)
    evidence_json: list[dict[str, Any]] = Field(
        sa_column=Column(JSON, nullable=False),
        default_factory=list,
    )
    dedupe_key: str = Field(max_length=255, index=True)
    target_wishlist_item_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="wishlist_items.id",
        index=True,
    )
    accepted_wishlist_item_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="wishlist_items.id",
    )
    created_at: datetime = Field(default_factory=utcnow, index=True)
    reviewed_at: datetime | None = Field(default=None, index=True)
