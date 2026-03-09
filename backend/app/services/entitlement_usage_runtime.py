from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlmodel import Session, select

from app.core.datetime_utils import utcnow
from app.models.entitlement_usage_daily import EntitlementUsageDaily


def consume_daily_quota(
    *,
    session: Session,
    user_id: UUID,
    feature_key: str,
    quota_limit: int | None,
    usage_date: date | None = None,
) -> tuple[bool, int]:
    """Consume one daily quota unit for a feature.

    Returns tuple: (allowed, used_count_after_attempt).
    """
    if quota_limit is None:
        return True, 0
    if quota_limit <= 0:
        return False, 0

    day = usage_date or utcnow().date()
    row = session.exec(
        select(EntitlementUsageDaily).where(
            EntitlementUsageDaily.user_id == user_id,
            EntitlementUsageDaily.feature_key == feature_key,
            EntitlementUsageDaily.usage_date == day,
        )
    ).first()
    if row is None:
        row = EntitlementUsageDaily(
            user_id=user_id,
            feature_key=feature_key,
            usage_date=day,
            used_count=0,
        )

    current = int(row.used_count or 0)
    if current >= quota_limit:
        return False, current

    row.used_count = current + 1
    row.updated_at = utcnow()
    session.add(row)
    return True, row.used_count
