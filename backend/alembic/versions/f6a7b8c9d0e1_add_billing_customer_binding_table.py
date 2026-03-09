"""Add billing customer binding table

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-02-16 22:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_customer_bindings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("provider_customer_id", sa.String(length=200), nullable=True),
        sa.Column("provider_subscription_id", sa.String(length=200), nullable=True),
        sa.Column("last_event_id", sa.String(length=200), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_customer_bindings_created_at",
        "billing_customer_bindings",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_updated_at",
        "billing_customer_bindings",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_provider",
        "billing_customer_bindings",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_user_id",
        "billing_customer_bindings",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_provider_customer_id",
        "billing_customer_bindings",
        ["provider_customer_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_provider_subscription_id",
        "billing_customer_bindings",
        ["provider_subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_billing_customer_bindings_last_seen_at",
        "billing_customer_bindings",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "uq_billing_customer_bindings_provider_customer",
        "billing_customer_bindings",
        ["provider", "provider_customer_id"],
        unique=True,
    )
    op.create_index(
        "uq_billing_customer_bindings_provider_subscription",
        "billing_customer_bindings",
        ["provider", "provider_subscription_id"],
        unique=True,
    )
    op.create_index(
        "uq_billing_customer_bindings_provider_user",
        "billing_customer_bindings",
        ["provider", "user_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_billing_customer_bindings_provider_user", table_name="billing_customer_bindings")
    op.drop_index("uq_billing_customer_bindings_provider_subscription", table_name="billing_customer_bindings")
    op.drop_index("uq_billing_customer_bindings_provider_customer", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_last_seen_at", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_provider_subscription_id", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_provider_customer_id", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_user_id", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_provider", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_updated_at", table_name="billing_customer_bindings")
    op.drop_index("ix_billing_customer_bindings_created_at", table_name="billing_customer_bindings")
    op.drop_table("billing_customer_bindings")
