# backend/app/models/card_session.py

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel
from sqlalchemy import Index
from app.models.card import CardRead
from app.core.datetime_utils import utcnow

class CardSessionStatus(str, Enum):
    PENDING = "PENDING"
    WAITING_PARTNER = "WAITING_PARTNER"
    COMPLETED = "COMPLETED"


class CardSessionMode(str, Enum):
    DAILY_RITUAL = "DAILY_RITUAL"
    DECK = "DECK"


class CardSessionBase(SQLModel):
    card_id: uuid.UUID = Field(foreign_key="cards.id")
    category: str
    mode: CardSessionMode = Field(default=CardSessionMode.DECK)
    status: CardSessionStatus = Field(default=CardSessionStatus.PENDING)

class CardSession(CardSessionBase, table=True):
    __tablename__ = "card_sessions"
    __table_args__ = (
        Index("ix_card_sessions_mode_created_at", "mode", "created_at"),
        Index("ix_card_sessions_creator_created_at", "creator_id", "created_at"),
        Index("ix_card_sessions_partner_created_at", "partner_id", "created_at"),
        Index("ix_card_sessions_status_created_at", "status", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    creator_id: uuid.UUID = Field(foreign_key="users.id")
    partner_id: Optional[uuid.UUID] = Field(foreign_key="users.id", default=None) # 確保 default=None
    created_at: datetime = Field(default_factory=utcnow)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)

class CardSessionRead(CardSessionBase):
    id: uuid.UUID
    creator_id: uuid.UUID
    created_at: datetime
    card: Optional[CardRead] = None 

# 這是你剛才沒貼完整的歷史紀錄模型
class DeckHistoryEntry(SQLModel):
    session_id: uuid.UUID
    card_title: str
    card_question: str
    category: str
    depth_level: int = 1
    my_answer: Optional[str] = None
    partner_answer: Optional[str] = None
    revealed_at: datetime
