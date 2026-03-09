# Module D3: Weekly report — completion rate, appreciation summary, optional AI insight.
# AI insight per docs/ai-safety/ai-guardrails.md (no blame/diagnosis).

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from app.models.appreciation import Appreciation
from app.models.daily_sync import DailySync
from sqlmodel import Session, select, func

logger = logging.getLogger(__name__)

DAYS_IN_WEEK = 7


def get_weekly_report(
    session: Session,
    current_user_id: UUID,
    partner_id: UUID | None,
) -> dict[str, Any]:
    """Compute completion rate (daily sync), appreciation count, for the last 7 days."""
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=DAYS_IN_WEEK - 1)
    # Daily sync: distinct days user filled in [start, today]
    current_sync_days = {
        value
        for value in session.exec(
            select(DailySync.sync_date).where(
                DailySync.user_id == current_user_id,
                DailySync.sync_date >= start,
                DailySync.sync_date <= today,
            )
        ).all()
    }
    filled_days = len(current_sync_days)
    completion_rate = min(1.0, filled_days / DAYS_IN_WEEK)

    partner_filled_days = 0
    pair_overlap_days = 0
    pair_sync_alignment_rate: float | None = None
    if partner_id:
        partner_sync_days = {
            value
            for value in session.exec(
                select(DailySync.sync_date).where(
                    DailySync.user_id == partner_id,
                    DailySync.sync_date >= start,
                    DailySync.sync_date <= today,
                )
            ).all()
        }
        partner_filled_days = len(partner_sync_days)
        pair_overlap_days = len(current_sync_days & partner_sync_days)
        pair_sync_alignment_rate = min(1.0, pair_overlap_days / DAYS_IN_WEEK)

    # Appreciation: sent or received in last 7 days
    period_start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
    appreciation_count = session.exec(
        select(func.count(Appreciation.id)).where(
            (Appreciation.user_id == current_user_id) | (Appreciation.partner_id == current_user_id),
            Appreciation.created_at >= period_start_dt,
        )
    ).one() or 0
    return {
        "period_start": start.isoformat(),
        "period_end": today.isoformat(),
        "daily_sync_completion_rate": round(completion_rate, 2),
        "daily_sync_days_filled": filled_days,
        "partner_daily_sync_days_filled": partner_filled_days,
        "pair_sync_overlap_days": pair_overlap_days,
        "pair_sync_alignment_rate": (round(pair_sync_alignment_rate, 2) if pair_sync_alignment_rate is not None else None),
        "appreciation_count": appreciation_count,
        "insight": None,  # filled by route if AI enabled
    }


async def generate_weekly_insight(
    completion_rate: float,
    appreciation_count: int,
) -> str | None:
    """One-line non-judgmental insight. Per docs/ai-safety/ai-guardrails.md."""
    try:
        from app.services.ai import client
        from app.core.config import settings
        if not (getattr(settings, "OPENAI_API_KEY", None) or "").strip():
            return None
        prompt = (
            "You are a relationship reflection helper. Given only these numbers: "
            "daily sync completion rate (0-1) = {:.2f}, appreciation messages this week = {}. "
            "Output exactly one short sentence in Traditional Chinese: a gentle, non-judgmental observation "
            "(e.g. pattern or encouragement). Do NOT assign blame, diagnose, or judge. "
            "Output only the sentence, no prefix."
        ).format(completion_rate, appreciation_count)
        completion = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=100,
        )
        text = (completion.choices[0].message.content or "").strip()
        return text[:200] if text else None
    except Exception as e:
        logger.warning("Weekly report AI insight failed: %s", type(e).__name__)
        return None
