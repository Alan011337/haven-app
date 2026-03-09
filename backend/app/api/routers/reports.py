# P2-I [ADMIN-02]: User-facing report submission; D3: Weekly report.

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep, verify_active_partner_id
from app.api.error_handling import commit_with_error_handling
from app.models.content_report import ContentReport, ContentReportStatus
from app.schemas.content_report import ReportSubmitRequest, ReportSubmitResponse
from app.services.weekly_report_runtime import get_weekly_report, generate_weekly_insight

router = APIRouter()
logger = logging.getLogger(__name__)

ALLOWED_RESOURCE_TYPES = frozenset({"whisper_wall", "deck_marketplace", "journal", "card"})


@router.post("", response_model=ReportSubmitResponse)
def submit_report(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    body: ReportSubmitRequest,
) -> ReportSubmitResponse:
    if body.resource_type not in ALLOWED_RESOURCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid resource_type.",
        )
    if not body.resource_id or len(body.resource_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="resource_id required, max 128 chars.",
        )
    report = ContentReport(
        resource_type=body.resource_type,
        resource_id=body.resource_id.strip(),
        reporter_user_id=current_user.id,
        reason=(body.reason or "").strip()[:500] or None,
        status=ContentReportStatus.PENDING.value,
    )
    session.add(report)
    commit_with_error_handling(
        session,
        logger=logger,
        action="submit_report",
        failure_detail="Unable to submit report.",
    )
    return ReportSubmitResponse(id=report.id, status=report.status)


@router.get("/weekly")
async def get_weekly_report_route(
    *,
    session: SessionDep,
    current_user: CurrentUser,
) -> dict[str, Any]:
    """D3: Weekly report — completion rate, appreciation count, optional one-line AI insight."""
    partner_id = verify_active_partner_id(session=session, current_user=current_user)
    data = get_weekly_report(session, current_user.id, partner_id)
    insight = await generate_weekly_insight(
        data["daily_sync_completion_rate"],
        data["appreciation_count"],
    )
    if insight:
        data["insight"] = insight
    return data
