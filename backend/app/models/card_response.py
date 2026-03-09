# backend/app/models/card_response.py

import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum 
from sqlalchemy import Column, Index

from app.core.datetime_utils import utcnow
from app.core.field_encryption import EncryptedText

if TYPE_CHECKING:
    from .user import User
    from .card import Card

# 👇 [新增] 定義狀態 Enum：決定是否給對方看
class ResponseStatus(str, Enum):
    PENDING = "PENDING"     # 鎖定中 (對方還沒寫)
    REVEALED = "REVEALED"   # 已解鎖 (雙方都寫了)

# 基礎模型
class CardResponseBase(SQLModel):
    content: str = Field(
        max_length=2000,
        sa_column=Column(EncryptedText(), nullable=False),
    )  # 使用者的回答內容
    session_id: Optional[uuid.UUID] = Field(default=None, foreign_key="card_sessions.id")
    is_initiator: bool = Field(default=False) # 👈 新增：紀錄誰是抽卡發起人
    # status: ResponseStatus = Field(default=ResponseStatus.PENDING) # 也可以放在這裡，但通常放在 table model 比較安全

class CardResponse(CardResponseBase, table=True):
    __tablename__ = "card_responses"
    __table_args__ = (
        Index("ix_card_responses_user_id", "user_id"),
        Index("ix_card_responses_card_id", "card_id"),
        Index("uq_card_responses_session_user", "session_id", "user_id", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    
    # 👇 [新增] 狀態欄位 (預設為 PENDING)
    status: ResponseStatus = Field(default=ResponseStatus.PENDING)

    # 關鍵關聯
    card_id: uuid.UUID = Field(foreign_key="cards.id")
    user_id: uuid.UUID = Field(foreign_key="users.id")
    
    # 關係連結
    user: "User" = Relationship(back_populates="card_responses")
    card: "Card" = Relationship(back_populates="responses")

class CardResponseCreate(CardResponseBase):
    card_id: uuid.UUID

class CardResponseRead(CardResponseBase):
    id: uuid.UUID
    card_id: uuid.UUID
    user_id: uuid.UUID
    content: str
    status: ResponseStatus # 👇 [新增] 讀取時也要回傳狀態
    created_at: datetime
    session_id: Optional[uuid.UUID]
