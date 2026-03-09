"""Add billing command and webhook receipt tables

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-02-16 21:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_command_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_plan", sa.String(length=100), nullable=True),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_command_logs_action",
        "billing_command_logs",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_billing_command_logs_created_at",
        "billing_command_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_billing_command_logs_idempotency_key",
        "billing_command_logs",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_billing_command_logs_user_id",
        "billing_command_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_billing_command_logs_user_idempotency",
        "billing_command_logs",
        ["user_id", "idempotency_key"],
        unique=True,
    )

    op.create_table(
        "billing_webhook_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("processed_at", sa.DateTime(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_event_id", sa.String(length=200), nullable=False),
        sa.Column("provider_event_type", sa.String(length=200), nullable=True),
        sa.Column("signature_header", sa.String(length=1000), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_webhook_receipts_provider",
        "billing_webhook_receipts",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_billing_webhook_receipts_provider_event_id",
        "billing_webhook_receipts",
        ["provider_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_webhook_receipts_received_at",
        "billing_webhook_receipts",
        ["received_at"],
        unique=False,
    )
    op.create_index(
        "uq_billing_webhook_receipts_provider_event",
        "billing_webhook_receipts",
        ["provider", "provider_event_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_billing_webhook_receipts_provider_event", table_name="billing_webhook_receipts")
    op.drop_index("ix_billing_webhook_receipts_received_at", table_name="billing_webhook_receipts")
    op.drop_index("ix_billing_webhook_receipts_provider_event_id", table_name="billing_webhook_receipts")
    op.drop_index("ix_billing_webhook_receipts_provider", table_name="billing_webhook_receipts")
    op.drop_table("billing_webhook_receipts")

    op.drop_index("uq_billing_command_logs_user_idempotency", table_name="billing_command_logs")
    op.drop_index("ix_billing_command_logs_user_id", table_name="billing_command_logs")
    op.drop_index("ix_billing_command_logs_idempotency_key", table_name="billing_command_logs")
    op.drop_index("ix_billing_command_logs_created_at", table_name="billing_command_logs")
    op.drop_index("ix_billing_command_logs_action", table_name="billing_command_logs")
    op.drop_table("billing_command_logs")
