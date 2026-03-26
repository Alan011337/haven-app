# backend/app/models/journal.py

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING, List
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, Index

from app.core.datetime_utils import utcnow
from app.core.field_encryption import EncryptedText

# 引入 AnalysisRead 用於 API 回傳 schema 定義
# 注意：這裡使用字串引用或是在 Pydantic 生成時處理
from app.models.analysis import AnalysisRead, Analysis

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.card import Card
    from app.models.journal_attachment import JournalAttachment

# 1. 基礎模型
class JournalBase(SQLModel):
    title: Optional[str] = None
    content: str = Field(sa_column=Column(EncryptedText(), nullable=False))
    is_draft: bool = Field(default=False)
    mood: Optional[str] = None # 這是使用者自己選的心情 (User Input)
    tags: Optional[str] = None
    visibility: str = Field(default="PARTNER_TRANSLATED_ONLY", index=True)
    content_format: str = Field(default="markdown")
    # TODO(legacy-naming): These "translation" fields now store the partner-facing
    # *adaptation* (not a literal translation).  Renaming requires a DB migration.
    partner_translation_status: str = Field(default="NOT_REQUESTED")
    partner_translated_content: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )

# 2. 資料庫模型 (Table)
class Journal(JournalBase, table=True):
    __tablename__ = "journals"
    # 🚀 Composite indexes for high-frequency query patterns:
    # - (user_id, deleted_at, created_at DESC) → read_my_journals, read_partner_journals, rate limit checks
    # - (user_id, created_at) → relationship weather hint lookback, LWW conflict detection
    __table_args__ = (
        Index("ix_journals_user_deleted_created", "user_id", "deleted_at", "created_at"),
        Index("ix_journals_user_created", "user_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)

    # Foreign Keys
    user_id: uuid.UUID = Field(foreign_key="users.id")
    deck_id: Optional[int] = Field(default=None, foreign_key="card_decks.id")
    card_id: Optional[uuid.UUID] = Field(default=None, foreign_key="cards.id")

    # Relationships
    user: "User" = Relationship(back_populates="journals")
    card: Optional["Card"] = Relationship(back_populates="journals")
    attachments: List["JournalAttachment"] = Relationship(
        back_populates="journal",
        sa_relationship_kwargs={
            "cascade": "all, delete-orphan",
            "order_by": "JournalAttachment.created_at.asc()",
        },
    )
    
    # 🔥 關鍵：透過關聯連結到 Analysis 表，並設定串聯刪除 (日記刪除，分析也刪除)
    analysis: Optional["Analysis"] = Relationship(
        back_populates="journal",
        sa_relationship_kwargs={"uselist": False, "cascade": "all, delete"}
    )

# 3. 讀取用的 Schema (API Response)
class JournalRead(JournalBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    user_id: uuid.UUID
    deck_id: Optional[int]
    card_id: Optional[uuid.UUID]
    
    # 🔥 API 會在這裡回傳完整的分析物件
    # 前端讀取方式會變成: journal.analysis.advice_for_user
    analysis: Optional[AnalysisRead] = None
