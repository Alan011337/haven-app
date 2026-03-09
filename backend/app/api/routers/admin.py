# READ_AUTHZ_MATRIX: GET /api/admin/users/{user_id}/status
# READ_AUTHZ_MATRIX: GET /api/admin/audit-events
# READ_AUTHZ_MATRIX: GET /api/admin/moderation/queue
# AUTHZ_MATRIX: POST /api/admin/users/{user_id}/unbind
# AUTHZ_MATRIX: POST /api/admin/moderation/{report_id}/resolve
# AUTHZ_DENY_MATRIX: POST /api/admin/users/{user_id}/unbind

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import func, select

from app.api.deps import CurrentAdminUser, CurrentAdminWriteUser, SessionDep, require_admin_user
from app.api.error_handling import commit_with_error_handling
from app.models.audit_event import AuditEvent
from app.models.card_response import CardResponse
from app.models.content_report import ContentReport, ContentReportStatus
from app.models.notification_event import NotificationEvent
from app.models.user import User
from app.models.journal import Journal
from app.schemas.admin import (
    AdminAuditEventPublic,
    AdminUnbindResult,
    AdminUserStatusPublic,
)
from app.schemas.content_report import ModerationReportPublic, ModerationResolveRequest, ModerationResolveResponse
from app.services.audit_log import record_audit_event
from app.services.lifecycle_solo_mode import transition_to_solo_mode
from app.core.datetime_utils import utcnow

router = APIRouter(dependencies=[Depends(require_admin_user)])
logger = logging.getLogger(__name__)


def _count_rows(session: SessionDep, statement) -> int:
    value = session.exec(statement).one()
    return int(value or 0)


@router.get("/users/{user_id}/status", response_model=AdminUserStatusPublic)
def read_admin_user_status(
    *,
    session: SessionDep,
    current_admin: CurrentAdminUser,
    user_id: uuid.UUID,
) -> AdminUserStatusPublic:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    journals_count = _count_rows(
        session,
        select(func.count()).select_from(Journal).where(Journal.user_id == user_id),
    )
    card_responses_count = _count_rows(
        session,
        select(func.count()).select_from(CardResponse).where(CardResponse.user_id == user_id),
    )
    notifications_count = _count_rows(
        session,
        select(func.count())
        .select_from(NotificationEvent)
        .where(NotificationEvent.receiver_user_id == user_id),
    )
    audit_events_count = _count_rows(
        session,
        select(func.count())
        .select_from(AuditEvent)
        .where(
            (AuditEvent.actor_user_id == user_id) | (AuditEvent.target_user_id == user_id)
        ),
    )

    record_audit_event(
        session=session,
        actor_user_id=current_admin.id,
        action="ADMIN_VIEW_USER_STATUS",
        resource_type="user",
        resource_id=user_id,
        target_user_id=user_id,
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="admin_view_user_status",
        failure_detail="Unable to persist admin audit event.",
    )

    return AdminUserStatusPublic(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
        deleted_at=user.deleted_at,
        partner_id=user.partner_id,
        journals_count=journals_count,
        card_responses_count=card_responses_count,
        notifications_count=notifications_count,
        audit_events_count=audit_events_count,
    )


@router.get("/audit-events", response_model=list[AdminAuditEventPublic])
def list_admin_audit_events(
    *,
    session: SessionDep,
    current_admin: CurrentAdminUser,
    limit: int = Query(default=50, ge=1, le=200),
    actor_user_id: Optional[uuid.UUID] = Query(default=None),
) -> list[AdminAuditEventPublic]:
    query = select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)
    if actor_user_id:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    rows = list(session.exec(query))

    record_audit_event(
        session=session,
        actor_user_id=current_admin.id,
        action="ADMIN_LIST_AUDIT_EVENTS",
        resource_type="audit_event",
        metadata={
            "limit": limit,
            "filtered_actor_user_id": str(actor_user_id) if actor_user_id else "",
            "returned_rows": len(rows),
        },
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="admin_list_audit_events",
        failure_detail="Unable to persist admin audit event.",
    )

    return [
        AdminAuditEventPublic(
            id=row.id,
            created_at=row.created_at,
            actor_user_id=row.actor_user_id,
            target_user_id=row.target_user_id,
            action=row.action,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            outcome=row.outcome.value,
            reason=row.reason,
        )
        for row in rows
    ]


@router.post("/users/{user_id}/unbind", response_model=AdminUnbindResult)
def admin_unbind_user_pair(
    *,
    session: SessionDep,
    current_admin: CurrentAdminWriteUser,
    user_id: uuid.UUID,
) -> AdminUnbindResult:
    user = session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    previous_partner_id = user.partner_id
    if not previous_partner_id:
        record_audit_event(
            session=session,
            actor_user_id=current_admin.id,
            action="ADMIN_UNBIND_PARTNER",
            resource_type="user",
            resource_id=user_id,
            target_user_id=user_id,
            metadata={"status": "noop", "reason": "no_partner"},
        )
        commit_with_error_handling(
            session,
            logger=logger,
            action="admin_unbind_partner_noop",
            failure_detail="Unable to persist admin audit event.",
        )
        return AdminUnbindResult(
            user_id=user_id,
            previous_partner_id=None,
            unbound_bidirectional=False,
        )

    partner = session.get(User, previous_partner_id)
    user.partner_id = None
    bidirectional = False
    if partner and partner.partner_id == user.id:
        partner.partner_id = None
        bidirectional = True
        session.add(partner)
    session.add(user)

    record_audit_event(
        session=session,
        actor_user_id=current_admin.id,
        action="ADMIN_UNBIND_PARTNER",
        resource_type="user",
        resource_id=user_id,
        target_user_id=previous_partner_id,
        metadata={
            "status": "updated",
            "previous_partner_id": str(previous_partner_id),
            "bidirectional": bidirectional,
        },
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="admin_unbind_partner",
        failure_detail="Unable to unbind user pair.",
    )

    transition_to_solo_mode(session=session, user_id=user_id)
    if bidirectional:
        transition_to_solo_mode(session=session, user_id=previous_partner_id)

    return AdminUnbindResult(
        user_id=user_id,
        previous_partner_id=previous_partner_id,
        unbound_bidirectional=bidirectional,
    )


# ----- P2-I [ADMIN-02] Content Moderation -----


@router.get("/moderation/queue", response_model=list[ModerationReportPublic])
def list_moderation_queue(
    *,
    session: SessionDep,
    current_admin: CurrentAdminUser,
    status_filter: Optional[str] = Query(default="pending", description="pending | approved | dismissed | hidden | all"),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[ModerationReportPublic]:
    query = select(ContentReport).order_by(ContentReport.created_at.desc()).limit(limit)
    if status_filter and status_filter != "all":
        query = query.where(ContentReport.status == status_filter)
    rows = list(session.exec(query))

    record_audit_event(
        session=session,
        actor_user_id=current_admin.id,
        action="ADMIN_LIST_MODERATION_QUEUE",
        resource_type="content_report",
        metadata={"status_filter": status_filter, "limit": limit, "returned": len(rows)},
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="admin_list_moderation_queue",
        failure_detail="Unable to persist admin audit event.",
    )

    return [
        ModerationReportPublic(
            id=r.id,
            created_at=r.created_at,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            reporter_user_id=r.reporter_user_id,
            reason=r.reason,
            status=r.status,
            reviewed_at=r.reviewed_at,
            reviewer_admin_id=r.reviewer_admin_id,
            resolution_note=r.resolution_note,
        )
        for r in rows
    ]


@router.post("/moderation/{report_id}/resolve", response_model=ModerationResolveResponse)
def resolve_moderation_report(
    *,
    session: SessionDep,
    current_admin: CurrentAdminWriteUser,
    report_id: uuid.UUID,
    body: ModerationResolveRequest,
) -> ModerationResolveResponse:
    report = session.get(ContentReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    if report.status != ContentReportStatus.PENDING.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report already resolved.")

    valid_statuses = {ContentReportStatus.APPROVED.value, ContentReportStatus.DISMISSED.value, ContentReportStatus.HIDDEN.value}
    if body.status not in valid_statuses:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="status must be approved, dismissed, or hidden.")

    report.status = body.status
    report.reviewed_at = utcnow()
    report.reviewer_admin_id = current_admin.id
    report.resolution_note = (body.resolution_note or "").strip()[:500] or None
    session.add(report)

    record_audit_event(
        session=session,
        actor_user_id=current_admin.id,
        action="ADMIN_RESOLVE_MODERATION",
        resource_type="content_report",
        resource_id=report_id,
        metadata={"resolution": body.status, "report_resource_type": report.resource_type, "report_resource_id": report.resource_id},
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="admin_resolve_moderation",
        failure_detail="Unable to resolve report.",
    )

    return ModerationResolveResponse(id=report.id, status=report.status)
