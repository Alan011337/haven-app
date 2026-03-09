"""Add billing webhook retry metadata columns.

Revision ID: h1core0000013
Revises: h1core0000012
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000013"
down_revision: Union[str, Sequence[str], None] = "h1core0000012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("next_attempt_at", sa.DateTime(), nullable=True),
    )
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("last_error_reason", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("payload_json", sa.Text(), nullable=True),
    )
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("provider_customer_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "billing_webhook_receipts",
        sa.Column("provider_subscription_id", sa.String(length=200), nullable=True),
    )
    op.create_index(
        "ix_billing_webhook_receipts_status_next_attempt_at",
        "billing_webhook_receipts",
        ["status", "next_attempt_at"],
    )
    op.create_index(
        "ix_billing_webhook_receipts_next_attempt_at",
        "billing_webhook_receipts",
        ["next_attempt_at"],
    )
    op.execute(
        sa.text(
            """
            UPDATE billing_webhook_receipts
            SET next_attempt_at = received_at
            WHERE next_attempt_at IS NULL
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS ix_billing_webhook_receipts_next_attempt_at"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_billing_webhook_receipts_status_next_attempt_at"))
    op.drop_column("billing_webhook_receipts", "provider_subscription_id")
    op.drop_column("billing_webhook_receipts", "provider_customer_id")
    op.drop_column("billing_webhook_receipts", "payload_json")
    op.drop_column("billing_webhook_receipts", "last_error_reason")
    op.drop_column("billing_webhook_receipts", "next_attempt_at")
    op.drop_column("billing_webhook_receipts", "attempt_count")
