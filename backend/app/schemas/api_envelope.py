from __future__ import annotations

from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    request_id: str = Field(default="-")


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ApiEnvelope(BaseModel, Generic[T]):
    data: Optional[T] = None
    meta: ApiMeta
    error: Optional[ApiError] = None

