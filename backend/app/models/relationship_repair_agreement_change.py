import uuid
from datetime import datetime

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class RelationshipRepairAgreementChange(SQLModel, table=True):
    __tablename__ = "relationship_repair_agreement_changes"
    # Two indexes below use a short `ix_rrac_` prefix because the default
    # `ix_<tablename>_<column>` name would exceed Postgres's 63-char identifier limit
    # (e.g. `ix_relationship_repair_agreement_changes_source_outcome_capture_id` = 66).
    __table_args__ = (
        Index(
            "ix_relationship_repair_agreement_changes_pair_changed_at",
            "user_id",
            "partner_id",
            "changed_at",
        ),
        Index(
            "ix_rrac_source_outcome_capture_id",
            "source_outcome_capture_id",
        ),
        Index(
            "ix_rrac_source_captured_by_user_id",
            "source_captured_by_user_id",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    repair_agreement_id: uuid.UUID = Field(foreign_key="relationship_repair_agreements.id", index=True)
    changed_by_user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    origin_kind: str = Field(max_length=64, index=True)
    # Indexed via explicit `Index` in __table_args__ with short `ix_rrac_` name (see note above).
    source_outcome_capture_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="relationship_repair_outcome_captures.id",
    )
    # Indexed via explicit `Index` in __table_args__ with short `ix_rrac_` name (see note above).
    source_captured_by_user_id: uuid.UUID | None = Field(default=None, foreign_key="users.id")
    source_captured_at: datetime | None = Field(default=None, index=True)
    changed_at: datetime = Field(default_factory=utcnow, index=True)
    protect_what_matters_before: str | None = Field(default=None, max_length=500)
    protect_what_matters_after: str | None = Field(default=None, max_length=500)
    avoid_in_conflict_before: str | None = Field(default=None, max_length=500)
    avoid_in_conflict_after: str | None = Field(default=None, max_length=500)
    repair_reentry_before: str | None = Field(default=None, max_length=500)
    repair_reentry_after: str | None = Field(default=None, max_length=500)
    # Optional short human-authored note attached to this change event.
    # Never mandatory, never AI-generated. Rendered as a quiet italic excerpt
    # in the Repair Agreements timeline entry when present.
    revision_note: str | None = Field(default=None, max_length=300)
