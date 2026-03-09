import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Index
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class BillingCommandLog(SQLModel, table=True):
    __tablename__ = "billing_command_logs"
    __table_args__ = (
        Index(
            "uq_billing_command_logs_user_idempotency",
            "user_id",
            "idempotency_key",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    processed_at: datetime = Field(default_factory=utcnow, nullable=False)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    action: str = Field(nullable=False, index=True, max_length=100)
    target_plan: Optional[str] = Field(default=None, nullable=True, max_length=100)
    idempotency_key: str = Field(nullable=False, index=True, max_length=200)
    payload_hash: str = Field(nullable=False, max_length=64)
    status: str = Field(default="APPLIED", nullable=False, max_length=32)


class BillingWebhookReceipt(SQLModel, table=True):
    __tablename__ = "billing_webhook_receipts"
    __table_args__ = (
        Index(
            "uq_billing_webhook_receipts_provider_event",
            "provider",
            "provider_event_id",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    received_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    processed_at: datetime = Field(default_factory=utcnow, nullable=False)

    provider: str = Field(nullable=False, index=True, max_length=32)
    provider_event_id: str = Field(nullable=False, index=True, max_length=200)
    provider_event_type: Optional[str] = Field(default=None, nullable=True, max_length=200)
    signature_header: str = Field(nullable=False, max_length=1000)
    payload_hash: str = Field(nullable=False, max_length=64)
    status: str = Field(default="PROCESSED", nullable=False, max_length=32)
    attempt_count: int = Field(default=0, nullable=False)
    next_attempt_at: Optional[datetime] = Field(default=None, nullable=True, index=True)
    last_error_reason: Optional[str] = Field(default=None, nullable=True, max_length=128)
    payload_json: Optional[str] = Field(default=None, nullable=True)
    provider_customer_id: Optional[str] = Field(default=None, nullable=True, max_length=200)
    provider_subscription_id: Optional[str] = Field(default=None, nullable=True, max_length=200)


class BillingEntitlementState(SQLModel, table=True):
    __tablename__ = "billing_entitlement_states"
    __table_args__ = (
        Index("uq_billing_entitlement_states_user_id", "user_id", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    lifecycle_state: str = Field(default="TRIAL", nullable=False, max_length=32, index=True)
    current_plan: Optional[str] = Field(default=None, nullable=True, max_length=100)
    last_command_id: Optional[uuid.UUID] = Field(default=None, nullable=True)
    revision: int = Field(default=1, nullable=False)


class BillingLedgerEntry(SQLModel, table=True):
    __tablename__ = "billing_ledger_entries"
    __table_args__ = (
        Index("uq_billing_ledger_entries_source_key", "source_key", unique=True),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    user_id: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id", nullable=True, index=True)
    source_type: str = Field(nullable=False, max_length=32, index=True)
    source_key: str = Field(nullable=False, max_length=255, index=True)

    action: Optional[str] = Field(default=None, nullable=True, max_length=100)
    previous_state: Optional[str] = Field(default=None, nullable=True, max_length=32)
    next_state: Optional[str] = Field(default=None, nullable=True, max_length=32)
    previous_plan: Optional[str] = Field(default=None, nullable=True, max_length=100)
    next_plan: Optional[str] = Field(default=None, nullable=True, max_length=100)

    payload_hash: Optional[str] = Field(default=None, nullable=True, max_length=64)


class BillingCustomerBinding(SQLModel, table=True):
    __tablename__ = "billing_customer_bindings"
    __table_args__ = (
        Index(
            "uq_billing_customer_bindings_provider_customer",
            "provider",
            "provider_customer_id",
            unique=True,
        ),
        Index(
            "uq_billing_customer_bindings_provider_subscription",
            "provider",
            "provider_subscription_id",
            unique=True,
        ),
        Index(
            "uq_billing_customer_bindings_provider_user",
            "provider",
            "user_id",
            unique=True,
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
    updated_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)

    provider: str = Field(nullable=False, index=True, max_length=32)
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)

    provider_customer_id: Optional[str] = Field(default=None, nullable=True, max_length=200, index=True)
    provider_subscription_id: Optional[str] = Field(default=None, nullable=True, max_length=200, index=True)

    last_event_id: Optional[str] = Field(default=None, nullable=True, max_length=200)
    last_seen_at: datetime = Field(default_factory=utcnow, nullable=False, index=True)
