# Module C1: Cooldown API schemas.

from pydantic import BaseModel, Field


class CooldownStartBody(BaseModel):
    duration_minutes: int = Field(ge=20, le=60, description="20–60 分鐘")


class CooldownStatusPublic(BaseModel):
    in_cooldown: bool
    started_by_me: bool
    ends_at_iso: str | None
    remaining_seconds: int | None


class CooldownRewriteBody(BaseModel):
    message: str = ""


class CooldownRewriteResponse(BaseModel):
    rewritten: str
