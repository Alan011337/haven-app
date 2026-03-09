# Module D2: Blueprint / wishlist schemas.

from pydantic import BaseModel, Field


class WishlistItemCreate(BaseModel):
    title: str = Field(max_length=500)
    notes: str = Field(max_length=2000, default="")


class WishlistItemPublic(BaseModel):
    id: str
    title: str
    notes: str
    created_at: str
    added_by_me: bool


class DateSuggestionPublic(BaseModel):
    suggested: bool
    message: str
    last_activity_at: str | None
    suggestions: list[str] = []
