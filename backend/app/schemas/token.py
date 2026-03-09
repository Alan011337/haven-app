# backend/app/schemas/token.py
from pydantic import BaseModel
from sqlmodel import SQLModel

# 這就是我們發給使用者的「通行證」格式
class Token(SQLModel):
    access_token: str
    token_type: str
    refresh_token: str | None = None
    refresh_expires_in: int | None = None


class RefreshTokenRequest(SQLModel):
    refresh_token: str

class TokenPayload(BaseModel):
    sub: str | None = None
