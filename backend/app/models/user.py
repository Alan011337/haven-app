import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlmodel import Field, SQLModel, Relationship

if TYPE_CHECKING:
    from app.models.journal import Journal
    from app.models.card_response import CardResponse
    # 如果未來 CardSession 需要反向查詢 User，也可以加在這裡

# 1. 基礎模型 (Base Schema)
# 我們把共用的欄位抽出來，這樣 User, UserRead, UserCreate 都不會漏掉重要欄位
class UserBase(SQLModel):
    email: str = Field(index=True, unique=True)
    full_name: Optional[str] = None
    is_active: bool = Field(default=True)
    deleted_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    
    # 你的自訂欄位 (完美保留)
    partner_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    savings_score: int = Field(default=0)
    invite_code: Optional[str] = Field(default=None, index=True, unique=True, nullable=True)
    invite_code_created_at: Optional[datetime] = Field(default=None, nullable=True)
    terms_accepted_at: Optional[datetime] = Field(default=None, nullable=True)
    birth_year: Optional[int] = Field(default=None, nullable=True)
    legacy_contact_email: Optional[str] = Field(default=None, nullable=True)  # LEGAL-02 數位遺產聯絡人

# 2. 資料庫模型 (Table)
class User(UserBase, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str

    # 關聯 (Relationships)
    journals: List["Journal"] = Relationship(back_populates="user")
    card_responses: List["CardResponse"] = Relationship(back_populates="user")

# 3. 讀取用 Schema (API Response)
# 這裡繼承 UserBase，所以前端會收到 savings_score 和 invite_code
class UserRead(UserBase):
    id: uuid.UUID

# 4. 建立用 Schema (註冊時)
class UserCreate(UserBase):
    password: str

# 5. 更新用 Schema (Patch)
class UserUpdate(SQLModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    partner_id: Optional[uuid.UUID] = None
    savings_score: Optional[int] = None
    invite_code: Optional[str] = None
    legacy_contact_email: Optional[str] = None  # LEGAL-02
