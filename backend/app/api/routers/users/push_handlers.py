from __future__ import annotations

import hashlib
import logging
import uuid
from time import perf_counter
from typing import Any

from fastapi import HTTPException, status
from sqlmodel import col, func, select

from app import models
from app.api.error_handling import commit_with_error_handling
from app.core.config import settings
from app.core.datetime_utils import utcnow
from app.models.audit_event import AuditEventOutcome
from app.models.push_subscription import PushSubscription, PushSubscriptionState
from app.schemas.notification import (
    PushDispatchDryRunRequest,
    PushDispatchDryRunResult,
    PushSubscriptionCreate,
    PushSubscriptionDeleteResult,
    PushSubscriptionPublic,
    PushSubscriptionUpsertResult,
)
from app.services.audit_log import record_audit_event_best_effort
from app.services.posthog_events import capture_posthog_event
from app.services.push_sli_runtime import push_runtime_metrics

logger = logging.getLogger(__name__)


def _hash_push_endpoint(endpoint: str) -> str:
    return hashlib.sha256(endpoint.encode("utf-8")).hexdigest()


def _build_push_subscription_public(row: PushSubscription) -> PushSubscriptionPublic:
    state_value = row.state
    if isinstance(state_value, PushSubscriptionState):
        normalized_state = state_value.value
    else:
        normalized_state = str(state_value)
    return PushSubscriptionPublic(
        id=row.id,
        endpoint_hash=row.endpoint_hash,
        state=normalized_state,
        failure_count=row.failure_count,
        fail_reason=row.fail_reason,
        last_success_at=row.last_success_at,
        last_failure_at=row.last_failure_at,
        dry_run_sampled_at=row.dry_run_sampled_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _coerce_push_state(value: object) -> PushSubscriptionState:
    if isinstance(value, PushSubscriptionState):
        return value
    if value is None:
        return PushSubscriptionState.ACTIVE
    try:
        return PushSubscriptionState(str(value))
    except ValueError:
        return PushSubscriptionState.ACTIVE


def handle_list_my_push_subscriptions(
    *,
    session,
    current_user: models.User,
    include_inactive: bool = True,
) -> list[PushSubscriptionPublic]:
    clauses: list[Any] = [
        PushSubscription.user_id == current_user.id,
        PushSubscription.state != PushSubscriptionState.PURGED,
    ]
    if not include_inactive:
        clauses.append(PushSubscription.state == PushSubscriptionState.ACTIVE)

    rows = session.exec(
        select(PushSubscription)
        .where(*clauses)
        .order_by(col(PushSubscription.created_at).desc())
    ).all()
    return [_build_push_subscription_public(row) for row in rows]


def handle_upsert_my_push_subscription(
    *,
    session,
    current_user: models.User,
    payload: PushSubscriptionCreate,
) -> PushSubscriptionUpsertResult:
    if not settings.PUSH_NOTIFICATIONS_ENABLED or not settings.WEBPUSH_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Push notification channel is disabled.",
        )

    endpoint = payload.endpoint.strip()
    if not endpoint.startswith("https://"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Push endpoint must use https.",
        )

    endpoint_hash = _hash_push_endpoint(endpoint)
    now = utcnow()
    created = False
    existing = session.exec(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    ).first()

    if existing:
        if existing.user_id != current_user.id:
            record_audit_event_best_effort(
                session=session,
                actor_user_id=current_user.id,
                target_user_id=existing.user_id,
                action="PUSH_SUBSCRIPTION_REGISTER_DENIED",
                resource_type="push_subscription",
                resource_id=existing.id,
                outcome=AuditEventOutcome.DENIED,
                reason="endpoint_owned_by_other_user",
                commit=True,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Push endpoint is already registered.",
            )
        subscription = existing
    else:
        existing_count = int(
            session.exec(
                select(func.count(PushSubscription.id)).where(
                    PushSubscription.user_id == current_user.id,
                    PushSubscription.state != PushSubscriptionState.PURGED,
                )
            ).one()
            or 0
        )
        if existing_count >= settings.PUSH_MAX_SUBSCRIPTIONS_PER_USER:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "Too many push subscriptions for this user. "
                    "Please remove old devices and try again."
                ),
            )

        subscription = PushSubscription(
            user_id=current_user.id,
            endpoint=endpoint,
            endpoint_hash=endpoint_hash,
            p256dh_key=payload.keys.p256dh.strip(),
            auth_key=payload.keys.auth.strip(),
            expiration_time=payload.expiration_time,
            user_agent=(payload.user_agent.strip() if payload.user_agent else None),
            state=PushSubscriptionState.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        created = True

    subscription.endpoint = endpoint
    subscription.endpoint_hash = endpoint_hash
    subscription.p256dh_key = payload.keys.p256dh.strip()
    subscription.auth_key = payload.keys.auth.strip()
    subscription.expiration_time = payload.expiration_time
    subscription.user_agent = payload.user_agent.strip() if payload.user_agent else None
    subscription.state = PushSubscriptionState.ACTIVE
    subscription.failure_count = 0
    subscription.fail_reason = None
    subscription.deleted_at = None
    subscription.updated_at = now
    session.add(subscription)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Upsert push subscription",
        conflict_detail="Push subscription conflict, please retry.",
        failure_detail="Push subscription update failed.",
    )
    session.refresh(subscription)
    push_runtime_metrics.record_subscription_upsert(created=created)
    capture_posthog_event(
        event_name="webpush_subscribed",
        distinct_id=str(current_user.id),
        properties={"created": created},
    )
    return PushSubscriptionUpsertResult(
        created=created,
        subscription=_build_push_subscription_public(subscription),
    )


def handle_dry_run_my_push_dispatch(
    *,
    session,
    current_user: models.User,
    payload: PushDispatchDryRunRequest,
) -> PushDispatchDryRunResult:
    started = perf_counter()
    sample_size = int(payload.sample_size or settings.PUSH_DRY_RUN_SAMPLE_SIZE)
    sample_size = max(1, min(sample_size, 20))
    ttl_seconds = int(payload.ttl_seconds or settings.PUSH_DEFAULT_TTL_SECONDS)
    ttl_seconds = max(60, min(ttl_seconds, settings.PUSH_JWT_MAX_EXP_SECONDS))
    enabled = bool(settings.PUSH_NOTIFICATIONS_ENABLED)

    active_rows = session.exec(
        select(PushSubscription)
        .where(
            PushSubscription.user_id == current_user.id,
            PushSubscription.state == PushSubscriptionState.ACTIVE,
        )
        .order_by(col(PushSubscription.updated_at).desc())
    ).all()
    if not enabled or not active_rows:
        push_runtime_metrics.record_dry_run(
            sampled_count=0,
            latency_ms=(perf_counter() - started) * 1000,
        )
        return PushDispatchDryRunResult(
            enabled=enabled,
            ttl_seconds=ttl_seconds,
            sampled_count=0,
            active_count=len(active_rows),
            sampled_subscription_ids=[],
        )

    sampled_rows = active_rows[:sample_size]
    sampled_ids = [row.id for row in sampled_rows]
    sampled_at = utcnow()
    for row in sampled_rows:
        row.dry_run_sampled_at = sampled_at
        row.updated_at = sampled_at
        session.add(row)

    commit_with_error_handling(
        session,
        logger=logger,
        action="Push dispatch dry-run",
        conflict_detail="Push dispatch dry-run conflict, please retry.",
        failure_detail="Push dispatch dry-run failed.",
    )
    push_runtime_metrics.record_dry_run(
        sampled_count=len(sampled_ids),
        latency_ms=(perf_counter() - started) * 1000,
    )
    return PushDispatchDryRunResult(
        enabled=enabled,
        ttl_seconds=ttl_seconds,
        sampled_count=len(sampled_ids),
        active_count=len(active_rows),
        sampled_subscription_ids=sampled_ids,
    )


def handle_delete_my_push_subscription(
    *,
    session,
    current_user: models.User,
    subscription_id: uuid.UUID,
) -> PushSubscriptionDeleteResult:
    row = session.get(PushSubscription, subscription_id)
    if not row or row.user_id != current_user.id:
        record_audit_event_best_effort(
            session=session,
            actor_user_id=current_user.id,
            target_user_id=(row.user_id if row else None),
            action="PUSH_SUBSCRIPTION_DELETE_DENIED",
            resource_type="push_subscription",
            resource_id=subscription_id,
            outcome=AuditEventOutcome.DENIED,
            reason="not_owner_or_missing",
            commit=True,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Push subscription not found")

    state_value = _coerce_push_state(row.state)
    if state_value == PushSubscriptionState.PURGED:
        push_runtime_metrics.record_subscription_delete(deleted=False)
        return PushSubscriptionDeleteResult(deleted=False, subscription_id=subscription_id)
    if state_value == PushSubscriptionState.TOMBSTONED and row.deleted_at is not None:
        push_runtime_metrics.record_subscription_delete(deleted=False)
        return PushSubscriptionDeleteResult(deleted=False, subscription_id=subscription_id)

    now = utcnow()
    row.state = PushSubscriptionState.TOMBSTONED
    row.deleted_at = now
    row.updated_at = now
    if not row.fail_reason:
        row.fail_reason = "user_opt_out"
    session.add(row)
    commit_with_error_handling(
        session,
        logger=logger,
        action="Delete push subscription",
        conflict_detail="Push subscription delete conflict, please retry.",
        failure_detail="Push subscription delete failed.",
    )
    push_runtime_metrics.record_subscription_delete(deleted=True)
    return PushSubscriptionDeleteResult(deleted=True, subscription_id=subscription_id)
