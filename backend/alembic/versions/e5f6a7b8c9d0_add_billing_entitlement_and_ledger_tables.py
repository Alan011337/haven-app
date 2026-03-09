"""Add billing entitlement and ledger tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-02-16 22:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_entitlement_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False),
        sa.Column("current_plan", sa.String(length=100), nullable=True),
        sa.Column("last_command_id", sa.Uuid(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_entitlement_states_lifecycle_state",
        "billing_entitlement_states",
        ["lifecycle_state"],
        unique=False,
    )
    op.create_index(
        "ix_billing_entitlement_states_updated_at",
        "billing_entitlement_states",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_billing_entitlement_states_user_id",
        "billing_entitlement_states",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_billing_entitlement_states_user_id",
        "billing_entitlement_states",
        ["user_id"],
        unique=True,
    )

    op.create_table(
        "billing_ledger_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("source_key", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("previous_state", sa.String(length=32), nullable=True),
        sa.Column("next_state", sa.String(length=32), nullable=True),
        sa.Column("previous_plan", sa.String(length=100), nullable=True),
        sa.Column("next_plan", sa.String(length=100), nullable=True),
        sa.Column("payload_hash", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_billing_ledger_entries_created_at",
        "billing_ledger_entries",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_billing_ledger_entries_source_key",
        "billing_ledger_entries",
        ["source_key"],
        unique=False,
    )
    op.create_index(
        "ix_billing_ledger_entries_source_type",
        "billing_ledger_entries",
        ["source_type"],
        unique=False,
    )
    op.create_index(
        "ix_billing_ledger_entries_user_id",
        "billing_ledger_entries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_billing_ledger_entries_source_key",
        "billing_ledger_entries",
        ["source_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_billing_ledger_entries_source_key", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_entries_user_id", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_entries_source_type", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_entries_source_key", table_name="billing_ledger_entries")
    op.drop_index("ix_billing_ledger_entries_created_at", table_name="billing_ledger_entries")
    op.drop_table("billing_ledger_entries")

    op.drop_index("uq_billing_entitlement_states_user_id", table_name="billing_entitlement_states")
    op.drop_index("ix_billing_entitlement_states_user_id", table_name="billing_entitlement_states")
    op.drop_index("ix_billing_entitlement_states_updated_at", table_name="billing_entitlement_states")
    op.drop_index("ix_billing_entitlement_states_lifecycle_state", table_name="billing_entitlement_states")
    op.drop_table("billing_entitlement_states")
