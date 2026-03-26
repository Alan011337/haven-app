# P2-C Memory Lane: Archive (timeline + calendar), Time Capsule, Relationship Report.

from datetime import date, datetime
from typing import Any, Literal, Optional

import logging
from fastapi import APIRouter, HTTPException, Query, status
from app.core import settings
from app.core import metrics
from app.api.deps import ReadSessionDep, CurrentUser, verify_active_partner_id
from app.services.journal_storage import (
    journal_storage_enabled,
    create_signed_journal_attachment_url,
)
from app.schemas.memory import (
    CalendarDay,
    CalendarResponse,
    TimelineResponse,
    TimeCapsuleResponse,
    TimeCapsuleMemory,
    RelationshipReportResponse,
)
from app.services.memory_archive import (
    get_unified_timeline,
    get_calendar_days,
    get_time_capsule_memory,
    get_relationship_report,
)
from app.services.pagination import InvalidPageCursorError

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    session: ReadSessionDep,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=100),
    before: Optional[datetime] = Query(None, description="ISO datetime cursor; items strictly before this time"),
    cursor: Optional[str] = Query(None, description="Opaque cursor for pagination (base64)"),
    detail_level: Literal["full", "summary"] = Query(
        "full",
        description="Payload detail level. Use summary to reduce response size for list views.",
    ),
    include_answers: bool = Query(
        True,
        description="Whether to include card answers in timeline card items.",
    ),
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    tz_offset_minutes: int = Query(
        0,
        ge=-720,
        le=840,
        description="JS Date.getTimezoneOffset() value. Aligns date-range filtering to the user's local day.",
    ),
) -> Any:
    """Unified feed: journals + card history (and future photos), sorted by time desc. Cursor-based pagination via before."""
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    # Feature flag: only pass opaque cursor to service when enabled.
    use_cursor = bool(getattr(settings, "TIMELINE_CURSOR_ENABLED", False))
    try:
        items, has_more, next_cursor = get_unified_timeline(
            session=session,
            user_id=current_user.id,
            partner_id=verified_pid,
            limit=limit,
            before=before,
            from_date=from_date,
            to_date=to_date,
            cursor=cursor if use_cursor else None,
            detail_level=detail_level,
            include_answers=include_answers,
            tz_offset_minutes=tz_offset_minutes,
        )
    except InvalidPageCursorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid timeline cursor.",
        ) from exc
    # Observability: count cursor usage and log minimal redacted context (no PII)
    if use_cursor:
        try:
            metrics.increment("timeline.cursor.requests")
            # redact user id to first 8 chars only for debug correlation (non-PII)
            u = str(current_user.id)
            redacted = u[:8]
            logger.info(
                "timeline.cursor.used user=%s items=%d has_more=%s",
                redacted,
                len(items),
                has_more,
            )
        except Exception:
            # metrics helper is best-effort; never raise
            logger.debug("metrics increment failed for timeline.cursor.requests")
    # Post-process: sign attachment URLs if Supabase storage is configured,
    # then strip internal storage_path from response.
    storage_ok = journal_storage_enabled()
    for item in items:
        if item.get("type") != "journal" or not item.get("attachments"):
            continue
        for att in item["attachments"]:
            sp = att.pop("storage_path", None)
            if storage_ok and sp:
                try:
                    att["url"] = await create_signed_journal_attachment_url(
                        sp,
                        expires_in=settings.JOURNAL_ATTACHMENT_SIGNED_URL_TTL_SECONDS,
                    )
                except Exception:
                    att["url"] = None
            else:
                att["url"] = None

    return TimelineResponse(items=items, has_more=has_more, next_cursor=next_cursor)


@router.get("/calendar", response_model=CalendarResponse)
def get_calendar(
    session: ReadSessionDep,
    current_user: CurrentUser,
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    tz_offset_minutes: int = Query(
        0,
        ge=-720,
        le=840,
        description="JS Date.getTimezoneOffset() value. Aligns calendar day grouping to the user's local day.",
    ),
) -> Any:
    """Days in month that have content, with mood color and counts."""
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    days_raw = get_calendar_days(
        session=session,
        user_id=current_user.id,
        partner_id=verified_pid,
        year=year,
        month=month,
        tz_offset_minutes=tz_offset_minutes,
    )
    days = [CalendarDay(**d) for d in days_raw]
    return CalendarResponse(year=year, month=month, days=days)


@router.get("/time-capsule", response_model=TimeCapsuleResponse)
def get_time_capsule(
    session: ReadSessionDep,
    current_user: CurrentUser,
) -> Any:
    """One year ago today: memories for the pair. Used for anniversary / 時光膠囊.

    Tries exact anniversary date first; if no content, widens to ±3 days.
    """
    from datetime import timedelta
    from app.core.datetime_utils import utcnow
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    today = utcnow().date()
    exact_date = today - timedelta(days=365)

    # Try exact anniversary date first
    memory = get_time_capsule_memory(
        session=session,
        user_id=current_user.id,
        partner_id=verified_pid,
        from_date=exact_date,
        to_date=exact_date,
    )

    # Fallback: widen to ±3 days if exact date has no content
    if not memory:
        memory = get_time_capsule_memory(
            session=session,
            user_id=current_user.id,
            partner_id=verified_pid,
            from_date=exact_date - timedelta(days=3),
            to_date=exact_date + timedelta(days=3),
        )

    if not memory:
        return TimeCapsuleResponse(available=False)
    return TimeCapsuleResponse(
        available=True,
        memory=TimeCapsuleMemory(
            date=exact_date,
            from_date=memory["from_date"],
            to_date=memory["to_date"],
            journals_count=memory["journals_count"],
            cards_count=memory["cards_count"],
            appreciations_count=memory["appreciations_count"],
            summary_text=memory["summary_text"],
            items=memory["items"],
        ),
    )


@router.get("/report", response_model=RelationshipReportResponse)
def get_relationship_report_route(
    session: ReadSessionDep,
    current_user: CurrentUser,
    period: str = Query("week", pattern="^(week|month)$"),
) -> Any:
    """AI 關係週報/月報：情緒趨勢、話題、健檢建議（建議為 placeholder，可接 AI 後續）。"""
    verified_pid = verify_active_partner_id(session=session, current_user=current_user)
    report = get_relationship_report(
        session=session,
        user_id=current_user.id,
        partner_id=verified_pid,
        period=period,
    )
    return RelationshipReportResponse(**report)
