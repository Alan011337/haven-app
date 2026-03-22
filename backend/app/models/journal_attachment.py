import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Index
from sqlmodel import Field, Relationship, SQLModel

from app.core.datetime_utils import utcnow

if TYPE_CHECKING:
    from app.models.journal import Journal


class JournalAttachmentBase(SQLModel):
    file_name: str
    mime_type: str
    size_bytes: int
    storage_path: str
    caption: Optional[str] = None


class JournalAttachment(JournalAttachmentBase, table=True):
    __tablename__ = "journal_attachments"
    __table_args__ = (
        Index(
            "ix_journal_attachments_journal_deleted_created",
            "journal_id",
            "deleted_at",
            "created_at",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)

    journal_id: uuid.UUID = Field(foreign_key="journals.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")

    journal: "Journal" = Relationship(back_populates="attachments")
