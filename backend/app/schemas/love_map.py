# Module D1: Love Map API schemas.

from pydantic import BaseModel, Field


LAYER_VALUES = ("safe", "medium", "deep")


class LoveMapCardSummary(BaseModel):
    id: str
    title: str
    description: str
    question: str
    depth_level: int
    layer: str  # safe | medium | deep


class LoveMapCardsResponse(BaseModel):
    safe: list[LoveMapCardSummary]
    medium: list[LoveMapCardSummary]
    deep: list[LoveMapCardSummary]


class LoveMapNotePublic(BaseModel):
    id: str
    layer: str
    content: str
    created_at: str
    updated_at: str


class LoveMapNoteCreate(BaseModel):
    layer: str = Field(..., pattern="^(safe|medium|deep)$")
    content: str = Field(max_length=5000, default="")


class LoveMapNoteUpdate(BaseModel):
    content: str = Field(max_length=5000)
