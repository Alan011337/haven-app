from __future__ import annotations

from datetime import timedelta
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from sqlalchemy import update as sqlalchemy_update
from sqlmodel import col, or_, select

from app import models
from app.api.error_handling import commit_with_error_handling
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.analysis import Analysis
from app.models.audit_event import AuditEvent, AuditEventOutcome
from app.models.card_response import CardResponse
from app.models.card_session import CardSession
from app.models.consent_receipt import ConsentReceipt
from app.models.journal import Journal
from app.models.notification_event import NotificationEvent
from app.models.user_onboarding_consent import UserOnboardingConsent
from app.schemas.consent_receipt import ConsentReceiptCreate, ConsentReceiptPublic
from app.schemas.user import DataEraseResult, DataExportPackagePublic
from app.schemas.user_onboarding_consent import (
    UserOnboardingConsentCreate,
    UserOnboardingConsentPublic,
)
from app.services.audit_log import record_audit_event, record_audit_event_best_effort
from app.services.data_deletion_lifecycle import soft_delete_user_data
from app.services.entitlement_runtime import evaluate_entitlement
from app.services.notification import invalidate_notification_preference_cache

VALID_CONSENT_TYPES = {"terms_of_service", "privacy_policy", "ai_analysis"}


def handle_export_my_data(
    *,
    session,
    current_user: models.User,
    build_user_public: Callable[..., Any],
) -> DataExportPackagePublic:
    export_entitlement = evaluate_entitlement(
        session=session,
        user_id=current_user.id,
        feature="export_enabled",
    )
    if not bool(export_entitlement.get("allowed", True)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Data export is not available on your current plan.",
        )

    exported_at = utcnow()
    expires_at = exported_at + timedelta(days=settings.DATA_EXPORT_EXPIRY_DAYS)

    journal_rows = session.exec(
        select(Journal)
        .where(
            Journal.user_id == current_user.id,
            Journal.deleted_at.is_(None),
        )
        .order_by(col(Journal.created_at).desc())
    ).all()
    journal_ids = [row.id for row in journal_rows]

    analysis_rows: list[Analysis] = []
    if journal_ids:
        analysis_rows = session.exec(
            select(Analysis)
            .where(
                col(Analysis.journal_id).in_(journal_ids),
                Analysis.deleted_at.is_(None),
            )
            .order_by(col(Analysis.created_at).desc())
        ).all()

    card_response_rows = session.exec(
        select(CardResponse)
        .where(
            CardResponse.user_id == current_user.id,
            CardResponse.deleted_at.is_(None),
        )
        .order_by(col(CardResponse.created_at).desc())
    ).all()

    card_session_rows = session.exec(
        select(CardSession)
        .where(
            (
                (CardSession.creator_id == current_user.id)
                | (CardSession.partner_id == current_user.id)
            ),
            CardSession.deleted_at.is_(None),
        )
        .order_by(col(CardSession.created_at).desc())
    ).all()

    notification_rows = session.exec(
        select(NotificationEvent)
        .where(
            (
                (NotificationEvent.receiver_user_id == current_user.id)
                | (NotificationEvent.sender_user_id == current_user.id)
            ),
            NotificationEvent.deleted_at.is_(None),
        )
        .order_by(col(NotificationEvent.created_at).desc())
    ).all()

    payload = DataExportPackagePublic(
        exported_at=exported_at,
        expires_at=expires_at,
        user=build_user_public(session=session, current_user=current_user),
        journals=[row.model_dump() for row in journal_rows],
        analyses=[row.model_dump() for row in analysis_rows],
        card_responses=[row.model_dump() for row in card_response_rows],
        card_sessions=[row.model_dump() for row in card_session_rows],
        notification_events=[row.model_dump() for row in notification_rows],
    )
    record_audit_event_best_effort(
        session=session,
        actor_user_id=current_user.id,
        action="USER_DATA_EXPORT",
        resource_type="user",
        resource_id=current_user.id,
        metadata={
            "journals": len(journal_rows),
            "analyses": len(analysis_rows),
            "card_responses": len(card_response_rows),
            "card_sessions": len(card_session_rows),
            "notification_events": len(notification_rows),
        },
        commit=True,
    )
    return payload


def handle_erase_my_data(
    *,
    session,
    current_user: models.User,
    logger,
    commit_with_error_handling_fn=commit_with_error_handling,
) -> DataEraseResult:
    user_id = current_user.id
    erased_at = utcnow()
    delete_mode = "hard_delete"

    if settings.DATA_SOFT_DELETE_ENABLED:
        soft_delete_result = soft_delete_user_data(
            session=session,
            current_user=current_user,
        )
        deleted_counts = soft_delete_result.deleted_counts
        erased_at = soft_delete_result.deleted_at
        delete_mode = "soft_delete"
    else:
        if current_user.partner_id:
            partner = session.get(models.User, current_user.partner_id)
            if partner and partner.partner_id == user_id:
                partner.partner_id = None
                session.add(partner)

        journal_rows = session.exec(select(Journal).where(Journal.user_id == user_id)).all()
        journal_ids = [row.id for row in journal_rows]

        analysis_rows: list[Analysis] = []
        if journal_ids:
            analysis_rows = session.exec(
                select(Analysis).where(col(Analysis.journal_id).in_(journal_ids))
            ).all()

        session_rows = session.exec(
            select(CardSession).where(
                (CardSession.creator_id == user_id) | (CardSession.partner_id == user_id)
            )
        ).all()
        session_ids = [row.id for row in session_rows]

        response_filters: list[Any] = [CardResponse.user_id == user_id]
        if session_ids:
            response_filters.append(col(CardResponse.session_id).in_(session_ids))
        card_response_rows = session.exec(
            select(CardResponse).where(or_(*response_filters))
        ).all()

        notification_rows = session.exec(
            select(NotificationEvent).where(
                (NotificationEvent.receiver_user_id == user_id)
                | (NotificationEvent.sender_user_id == user_id)
            )
        ).all()

        for row in analysis_rows:
            session.delete(row)
        for row in journal_rows:
            session.delete(row)
        for row in card_response_rows:
            session.delete(row)
        for row in session_rows:
            session.delete(row)
        for row in notification_rows:
            session.delete(row)

        session.exec(
            sqlalchemy_update(AuditEvent)
            .where(AuditEvent.actor_user_id == user_id)
            .values(actor_user_id=None)
        )
        session.exec(
            sqlalchemy_update(AuditEvent)
            .where(AuditEvent.target_user_id == user_id)
            .values(target_user_id=None)
        )

        session.delete(current_user)
        deleted_counts = {
            "analyses": len(analysis_rows),
            "journals": len(journal_rows),
            "card_responses": len(card_response_rows),
            "card_sessions": len(session_rows),
            "notification_events": len(notification_rows),
            "users": 1,
        }

    record_audit_event(
        session=session,
        actor_user_id=None,
        action="USER_DATA_ERASE",
        resource_type="user",
        resource_id=user_id,
        metadata={
            "erased_user_id": str(user_id),
            "delete_mode": delete_mode,
            **deleted_counts,
        },
    )
    try:
        commit_with_error_handling_fn(
            session,
            logger=logger,
            action="Erase user data",
            conflict_detail="資料刪除時發生衝突，請稍後再試。",
            failure_detail="資料刪除失敗，請稍後再試。",
        )
    except HTTPException as exc:
        session.rollback()
        status_code = getattr(exc, "status_code", None)
        reason = f"http_{status_code}" if isinstance(status_code, int) else exc.__class__.__name__
        record_audit_event_best_effort(
            session=session,
            actor_user_id=None,
            action="USER_DATA_ERASE_ERROR",
            resource_type="user",
            resource_id=user_id,
            outcome=AuditEventOutcome.ERROR,
            reason=reason,
            metadata={
                "erased_user_id": str(user_id),
                "delete_mode": delete_mode,
            },
            commit=True,
        )
        raise

    return DataEraseResult(
        status="soft_deleted" if delete_mode == "soft_delete" else "erased",
        erased_at=erased_at,
        deleted_user_id=user_id,
        deleted_counts=deleted_counts,
    )


def handle_list_my_consents(
    *,
    session,
    current_user: models.User,
) -> list[ConsentReceiptPublic]:
    rows = session.exec(
        select(ConsentReceipt)
        .where(ConsentReceipt.user_id == current_user.id)
        .order_by(col(ConsentReceipt.granted_at).desc())
    ).all()
    return [ConsentReceiptPublic.model_validate(row) for row in rows]


def handle_create_consent_receipt(
    *,
    session,
    current_user: models.User,
    consent_in: ConsentReceiptCreate,
    request: Request,
    logger,
    resolve_client_ip: Callable[[Request], str],
) -> ConsentReceiptPublic:
    if consent_in.consent_type not in VALID_CONSENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無效的同意類型。有效值為：{', '.join(sorted(VALID_CONSENT_TYPES))}",
        )
    if not consent_in.policy_version.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="政策版本不可為空。",
        )

    client_ip = resolve_client_ip(request)
    receipt = ConsentReceipt(
        user_id=current_user.id,
        consent_type=consent_in.consent_type,
        policy_version=consent_in.policy_version.strip(),
        granted_at=utcnow(),
        ip_address=client_ip,
    )
    session.add(receipt)
    record_audit_event(
        session=session,
        actor_user_id=current_user.id,
        action="USER_CONSENT_GRANT",
        resource_type="consent_receipt",
        metadata={
            "consent_type": consent_in.consent_type,
            "policy_version": consent_in.policy_version.strip(),
        },
    )
    commit_with_error_handling(
        session,
        logger=logger,
        action="Create consent receipt",
        conflict_detail="同意紀錄建立時發生衝突，請稍後再試。",
        failure_detail="同意紀錄建立失敗，請稍後再試。",
    )
    session.refresh(receipt)
    return ConsentReceiptPublic.model_validate(receipt)


def handle_get_my_onboarding_consent(
    *,
    session,
    current_user: models.User,
) -> UserOnboardingConsentPublic | None:
    row = session.get(UserOnboardingConsent, current_user.id)
    if not row:
        return None
    return UserOnboardingConsentPublic.model_validate(row)


def handle_upsert_my_onboarding_consent(
    *,
    session,
    current_user: models.User,
    body: UserOnboardingConsentCreate,
    logger,
) -> UserOnboardingConsentPublic:
    allowed_freq = {"off", "low", "normal", "high"}
    allowed_ai = {"gentle", "direct"}
    if body.notification_frequency not in allowed_freq:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"notification_frequency must be one of: {', '.join(sorted(allowed_freq))}",
        )
    if body.ai_intensity not in allowed_ai:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ai_intensity must be one of: {', '.join(sorted(allowed_ai))}",
        )
    row = session.get(UserOnboardingConsent, current_user.id)
    if row:
        row.privacy_scope_accepted = body.privacy_scope_accepted
        row.notification_frequency = body.notification_frequency
        row.ai_intensity = body.ai_intensity
        row.updated_at = utcnow()
        session.add(row)
    else:
        row = UserOnboardingConsent(
            user_id=current_user.id,
            privacy_scope_accepted=body.privacy_scope_accepted,
            notification_frequency=body.notification_frequency,
            ai_intensity=body.ai_intensity,
        )
        session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Upsert onboarding consent",
        conflict_detail="設定儲存時發生衝突，請稍後再試。",
        failure_detail="設定儲存失敗，請稍後再試。",
    )
    session.refresh(row)
    invalidate_notification_preference_cache(current_user.id)
    return UserOnboardingConsentPublic.model_validate(row)
