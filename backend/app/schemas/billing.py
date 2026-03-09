import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class BillingStateChangeRequest(SQLModel):
    action: str = Field(min_length=1, max_length=100)
    target_plan: Optional[str] = Field(default=None, max_length=100)
    model_config = {"extra": "forbid"}


class BillingStateChangeResult(SQLModel):
    status: str
    idempotency_replayed: bool
    command_id: uuid.UUID
    idempotency_key: str
    action: str
    lifecycle_state: Optional[str] = None
    current_plan: Optional[str] = None
    target_plan: Optional[str] = None
    processed_at: datetime


class BillingWebhookResult(SQLModel):
    status: str
    replayed: bool
    processing_mode: str = "INLINE"
    provider: str
    event_id: str
    event_type: Optional[str] = None
    received_at: datetime


class BillingReconciliationResult(SQLModel):
    user_id: uuid.UUID
    checked_at: datetime
    command_count: int
    command_ledger_count: int
    missing_command_ledger_count: int
    missing_command_ids: list[uuid.UUID] = Field(default_factory=list)
    entitlement_state: Optional[str] = None
    entitlement_plan: Optional[str] = None
    healthy: bool


class BillingEntitlementSnapshot(SQLModel):
    plan: str
    quotas: dict[str, object] = Field(default_factory=dict)


class CreateCheckoutSessionRequest(SQLModel):
    """Request body for create-checkout-session; all fields optional, fallback to env."""
    price_id: Optional[str] = Field(default=None, max_length=200)
    success_url: Optional[str] = Field(default=None, max_length=500)
    cancel_url: Optional[str] = Field(default=None, max_length=500)
    model_config = {"extra": "forbid"}


class CreateCheckoutSessionResult(SQLModel):
    url: str = Field(min_length=1, max_length=2000)


class CreatePortalSessionRequest(SQLModel):
    """Request body for create-portal-session; return_url optional."""
    return_url: Optional[str] = Field(default=None, max_length=500)
    model_config = {"extra": "forbid"}


class CreatePortalSessionResult(SQLModel):
    url: str = Field(min_length=1, max_length=2000)
