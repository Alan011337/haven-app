from __future__ import annotations

import json
import logging
from typing import Callable, Optional

from fastapi import BackgroundTasks, HTTPException, Request, status
from sqlmodel import select

from app.api.deps import SessionDep
from app.api.error_handling import commit_with_error_handling
from app.core.datetime_utils import utcnow
from app.models.audit_event import AuditEventOutcome
from app.models.billing import BillingWebhookReceipt
from app.schemas.billing import BillingWebhookResult
from app.services.billing_transitions import hash_payload


async def handle_stripe_webhook_request(
    *,
    session: SessionDep,
    request: Request,
    background_tasks: BackgroundTasks,
    stripe_signature: Optional[str],
    webhook_secret: str,
    async_mode_enabled: bool,
    verify_stripe_signature_or_raise: Callable[..., None],
    audit_billing_webhook_issue: Callable[..., None],
    extract_customer_identifier_from_webhook_payload: Callable[[dict], Optional[str]],
    extract_subscription_identifier_from_webhook_payload: Callable[..., Optional[str]],
    webhook_processing_mode_for_status: Callable[[str], str],
    enqueue_stripe_webhook_processing: Callable[..., None],
    apply_stripe_webhook_effects: Callable[..., None],
    logger: logging.Logger,
) -> BillingWebhookResult:
    if not webhook_secret:
        audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.ERROR,
            reason="secret_not_configured",
            detail="Billing webhook secret is not configured.",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing webhook secret is not configured.",
        )
    if not stripe_signature:
        audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="missing_signature_header",
            detail="Stripe-Signature header is required.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Stripe-Signature header is required.",
        )

    body = await request.body()
    try:
        verify_stripe_signature_or_raise(
            payload=body,
            signature_header=stripe_signature,
            secret=webhook_secret,
        )
    except HTTPException as exc:
        audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="signature_verification_failed",
            detail=str(exc.detail),
        )
        raise

    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="invalid_json_payload",
            detail="Invalid webhook JSON payload.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook JSON payload.",
        ) from exc

    event_id = str(payload.get("id") or "").strip()
    if not event_id:
        audit_billing_webhook_issue(
            session=session,
            outcome=AuditEventOutcome.DENIED,
            reason="missing_event_id",
            detail="Webhook payload missing required event id.",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload missing required event id.",
        )

    event_type_raw = payload.get("type")
    event_type = str(event_type_raw).strip() if event_type_raw is not None else None
    payload_hash = hash_payload(body)
    provider_name = "STRIPE"
    provider_customer_id = extract_customer_identifier_from_webhook_payload(payload)
    provider_subscription_id = extract_subscription_identifier_from_webhook_payload(
        payload,
        event_type=event_type,
    )

    existing = session.exec(
        select(BillingWebhookReceipt).where(
            BillingWebhookReceipt.provider == provider_name,
            BillingWebhookReceipt.provider_event_id == event_id,
        )
    ).first()
    if existing:
        if existing.payload_hash != payload_hash:
            audit_billing_webhook_issue(
                session=session,
                outcome=AuditEventOutcome.DENIED,
                reason="replay_payload_mismatch",
                detail="Webhook replay payload mismatch.",
                metadata={"event_id": event_id},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Webhook replay payload mismatch.",
            )
        return BillingWebhookResult(
            status=existing.status,
            replayed=True,
            processing_mode=webhook_processing_mode_for_status(existing.status),
            provider=existing.provider,
            event_id=existing.provider_event_id,
            event_type=existing.provider_event_type,
            received_at=existing.received_at,
        )

    initial_receipt_status = "QUEUED" if async_mode_enabled else "PROCESSING"
    receipt = BillingWebhookReceipt(
        provider=provider_name,
        provider_event_id=event_id,
        provider_event_type=event_type,
        signature_header=stripe_signature,
        payload_hash=payload_hash,
        payload_json=body.decode("utf-8"),
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
        attempt_count=0,
        next_attempt_at=utcnow(),
        last_error_reason=None,
        status=initial_receipt_status,
        processed_at=utcnow(),
    )
    session.add(receipt)

    if async_mode_enabled:
        commit_with_error_handling(
            session,
            logger=logger,
            action="Stripe webhook enqueue",
            conflict_detail="Billing webhook enqueue conflict. Please retry.",
            failure_detail="Billing webhook enqueue failed.",
        )
        session.refresh(receipt)
        enqueue_stripe_webhook_processing(
            background_tasks=background_tasks,
            receipt_id=receipt.id,
            provider_name=provider_name,
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            payload_hash=payload_hash,
            provider_customer_id=provider_customer_id,
            provider_subscription_id=provider_subscription_id,
        )
        return BillingWebhookResult(
            status=receipt.status,
            replayed=False,
            processing_mode="ASYNC",
            provider=receipt.provider,
            event_id=receipt.provider_event_id,
            event_type=receipt.provider_event_type,
            received_at=receipt.received_at,
        )

    apply_stripe_webhook_effects(
        session=session,
        provider_name=provider_name,
        event_id=event_id,
        event_type=event_type,
        payload=payload,
        payload_hash=payload_hash,
        provider_customer_id=provider_customer_id,
        provider_subscription_id=provider_subscription_id,
    )
    receipt.status = "PROCESSED"
    receipt.processed_at = utcnow()
    session.add(receipt)

    commit_with_error_handling(
        session,
        logger=logger,
        action="Stripe webhook",
        conflict_detail="Billing webhook conflict. Please retry.",
        failure_detail="Billing webhook handling failed.",
    )
    session.refresh(receipt)

    return BillingWebhookResult(
        status=receipt.status,
        replayed=False,
        processing_mode="INLINE",
        provider=receipt.provider,
        event_id=receipt.provider_event_id,
        event_type=receipt.provider_event_type,
        received_at=receipt.received_at,
    )
