# Module B2: Appreciation Bank schemas.

from datetime import datetime
from sqlmodel import SQLModel


class AppreciationCreate(SQLModel):
    body_text: str
    model_config = {"extra": "forbid"}


class AppreciationPublic(SQLModel):
    id: int
    body_text: str
    created_at: datetime
