# backend/app/schemas/user.py

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlmodel import Field, SQLModel
from pydantic import EmailStr

# --- 1. 基礎模型 ---
class UserBase(SQLModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool = True

# --- 2. 註冊用 (前端傳密碼進來) ---
class UserCreate(SQLModel):
    email: EmailStr
    full_name: Optional[str] = None
    password: str = Field(min_length=8, max_length=128)
    age_confirmed: bool
    agreed_to_terms: bool = False
    birth_year: Optional[int] = None
    terms_version: str
    privacy_version: str
    model_config = {"extra": "forbid"}

# --- 3. 讀取用 (回傳給前端) ---
# 繼承 UserBase，所以自動擁有 email, full_name, is_active
class UserPublic(UserBase):
    id: uuid.UUID
    partner_id: Optional[uuid.UUID] = None
    savings_score: int = 0
    legacy_contact_email: Optional[str] = None  # LEGAL-02 數位遺產聯絡人

    partner_name: Optional[str] = None
    mode: Optional[str] = None

# --- 4. 配對相關 ---
class InviteCodeResponse(SQLModel):
    code: str
    expires_at: datetime

class PairingRequest(SQLModel):
    invite_code: str
    model_config = {"extra": "forbid"}


class DataExportPackagePublic(SQLModel):
    export_version: str = "v1"
    exported_at: datetime
    expires_at: datetime
    user: UserPublic
    journals: List[Dict[str, Any]] = Field(default_factory=list)
    analyses: List[Dict[str, Any]] = Field(default_factory=list)
    card_responses: List[Dict[str, Any]] = Field(default_factory=list)
    card_sessions: List[Dict[str, Any]] = Field(default_factory=list)
    notification_events: List[Dict[str, Any]] = Field(default_factory=list)


class DataEraseResult(SQLModel):
    status: str
    erased_at: datetime
    deleted_user_id: uuid.UUID
    deleted_counts: Dict[str, int] = Field(default_factory=dict)
