"""Binding helpers extracted from billing router to reduce route coupling."""

from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlmodel import select

from app.api.deps import SessionDep
from app.core.datetime_utils import utcnow
from app.models.billing import BillingCustomerBinding


def resolve_user_id_from_binding(
    *,
    session: SessionDep,
    provider: str,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
) -> Optional[uuid.UUID]:
    customer_user_id: Optional[uuid.UUID] = None
    subscription_user_id: Optional[uuid.UUID] = None

    if provider_customer_id:
        by_customer = session.exec(
            select(BillingCustomerBinding).where(
                BillingCustomerBinding.provider == provider,
                BillingCustomerBinding.provider_customer_id == provider_customer_id,
            )
        ).first()
        if by_customer:
            customer_user_id = by_customer.user_id

    if provider_subscription_id:
        by_subscription = session.exec(
            select(BillingCustomerBinding).where(
                BillingCustomerBinding.provider == provider,
                BillingCustomerBinding.provider_subscription_id == provider_subscription_id,
            )
        ).first()
        if by_subscription:
            subscription_user_id = by_subscription.user_id

    if customer_user_id and subscription_user_id and customer_user_id != subscription_user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing binding identifiers map to different users.",
        )

    return customer_user_id or subscription_user_id


def upsert_billing_customer_binding(
    *,
    session: SessionDep,
    provider: str,
    user_id: uuid.UUID,
    provider_customer_id: Optional[str],
    provider_subscription_id: Optional[str],
    event_id: str,
) -> None:
    binding_by_customer: Optional[BillingCustomerBinding] = None
    binding_by_subscription: Optional[BillingCustomerBinding] = None
    binding_by_user: Optional[BillingCustomerBinding] = None
    if provider_customer_id:
        binding_by_customer = session.exec(
            select(BillingCustomerBinding).where(
                BillingCustomerBinding.provider == provider,
                BillingCustomerBinding.provider_customer_id == provider_customer_id,
            )
        ).first()
    if provider_subscription_id:
        binding_by_subscription = session.exec(
            select(BillingCustomerBinding).where(
                BillingCustomerBinding.provider == provider,
                BillingCustomerBinding.provider_subscription_id == provider_subscription_id,
            )
        ).first()
    binding_by_user = session.exec(
        select(BillingCustomerBinding).where(
            BillingCustomerBinding.provider == provider,
            BillingCustomerBinding.user_id == user_id,
        )
    ).first()

    if binding_by_customer and binding_by_customer.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing customer binding conflict.",
        )
    if binding_by_subscription and binding_by_subscription.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing subscription binding conflict.",
        )
    if (
        binding_by_customer
        and binding_by_subscription
        and binding_by_customer.id != binding_by_subscription.id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing binding conflict between customer and subscription identifiers.",
        )

    binding = binding_by_customer or binding_by_subscription or binding_by_user

    if binding and binding.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Billing customer binding conflict.",
        )

    now = utcnow()
    if binding:
        binding.updated_at = now
        binding.last_seen_at = now
        binding.last_event_id = event_id
        if provider_customer_id:
            binding.provider_customer_id = provider_customer_id
        if provider_subscription_id:
            binding.provider_subscription_id = provider_subscription_id
        session.add(binding)
        return

    if not provider_customer_id and not provider_subscription_id:
        return

    session.add(
        BillingCustomerBinding(
            provider=provider,
            user_id=user_id,
            provider_customer_id=provider_customer_id,
            provider_subscription_id=provider_subscription_id,
            last_event_id=event_id,
            last_seen_at=now,
        )
    )
