# backend/app/models/card.py

import uuid
from typing import Optional, List, TYPE_CHECKING
from pydantic import field_validator
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum
from datetime import datetime
from sqlalchemy import Column, JSON
from app.core.datetime_utils import utcnow

# 為了避免循環引用，只在型別檢查時匯入
if TYPE_CHECKING:
    from .card_response import CardResponse
    from .journal import Journal  # 👈 新增這行，讓 Card 知道 Journal 的存在

# 1. 定義八大卡片類別 Enum
class CardCategory(str, Enum):
    DAILY_VIBE = "DAILY_VIBE"           # 日常共感
    SOUL_DIVE = "SOUL_DIVE"             # 靈魂深潛
    SAFE_ZONE = "SAFE_ZONE"             # 安全屋
    MEMORY_LANE = "MEMORY_LANE"         # 時光機
    GROWTH_QUEST = "GROWTH_QUEST"       # 共同成長
    AFTER_DARK = "AFTER_DARK"           # 深夜話題
    CO_PILOT = "CO_PILOT"               # 最佳副駕
    LOVE_BLUEPRINT = "LOVE_BLUEPRINT"   # 愛情藍圖

# 2. 基礎模型
class CardBase(SQLModel):
    category: CardCategory = Field(index=True)
    title: str
    description: str
    question: str
    difficulty_level: int = Field(default=1)
    depth_level: int = Field(default=1)
    tags: List[str] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    is_ai_generated: bool = Field(default=False) 

# 3. 牌組模型 (CardDeck)
# 🔥 修改順序：將被引用的表放在前面，符合 SQL 邏輯，程式碼更清晰
class CardDeck(SQLModel, table=True):
    __tablename__ = "card_decks"  # 👈 這是表名，必須跟 foreign_key 對應
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None

# 4. 卡片模型 (Card)
class Card(CardBase, table=True):
    __tablename__ = "cards"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(
        default_factory=utcnow,
        nullable=False
    )
    
    # 加上 index=True 提升查詢效能
    deck_id: Optional[int] = Field(default=None, foreign_key="card_decks.id", index=True)

    responses: List["CardResponse"] = Relationship(back_populates="card")
    journals: List["Journal"] = Relationship(back_populates="card")

# 5. Schema 用
class CardCreate(CardBase):
    pass

class CardRead(CardBase):
    id: uuid.UUID
    deck_id: Optional[int] = None

    @field_validator("tags", mode="before")
    @classmethod
    def tags_none_to_list(cls, v: object) -> List[str]:
        if v is None:
            return []
        return v if isinstance(v, list) else list(v)
