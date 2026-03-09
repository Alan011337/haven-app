"""Pure helper utilities for cards router."""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional

from fastapi import HTTPException, status


def normalize_category_or_raise(
    category: Optional[str],
    *,
    valid_values: set[str],
) -> Optional[str]:
    if category is None:
        return None
    normalized = category.strip().upper()
    if not normalized:
        return None
    if normalized not in valid_values:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無效的分類：{category}",
        )
    return normalized


def get_today_range(*, now_utc: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(now_utc.date(), time.min)
    end = datetime.combine(now_utc.date(), time.max)
    return start, end
