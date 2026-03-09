# backend/app/models/analysis.py

import uuid
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column

from app.core.datetime_utils import utcnow
from app.core.field_encryption import EncryptedText

if TYPE_CHECKING:
    from app.models.journal import Journal

# 1. 基礎欄位 (保留你原本的欄位設計)
class AnalysisBase(SQLModel):
    mood_label: Optional[str] = None
    emotional_needs: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )
    advice_for_user: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )
    action_for_user: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )
    advice_for_partner: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )
    action_for_partner: Optional[str] = Field(
        default=None,
        sa_column=Column(EncryptedText(), nullable=True),
    )
    card_recommendation: Optional[str] = None
    
    # 版本控制與安全
    safety_tier: int = Field(default=0)
    conflict_risk_detected: bool = Field(default=False)  # P2-D: 高風險關鍵字觸發調解模式
    prompt_version: Optional[str] = None
    model_version: Optional[str] = None
    parse_success: bool = Field(default=False)

# 2. 資料庫模型
class Analysis(AnalysisBase, table=True):
    __tablename__ = "analyses"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    
    # Foreign Keys
    # 注意：我們只需要 journal_id，因為透過 journal 就能找到 user
    journal_id: uuid.UUID = Field(foreign_key="journals.id", unique=True) # 一篇日記對應一個分析

    # Relationship
    journal: "Journal" = Relationship(back_populates="analysis")

# 3. 讀取用的 Schema (API 回傳用)
class AnalysisRead(AnalysisBase):
    id: uuid.UUID
    created_at: datetime
