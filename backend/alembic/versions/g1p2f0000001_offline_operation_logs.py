"""P2-F: Offline-first idempotency table for journal/card write replay

Revision ID: g1p2f0000001
Revises: g1p2d0000001
Create Date: 2026-02-23

- offline_operation_logs: (user_id, idempotency_key) unique, response_payload JSON
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g1p2f0000001"
down_revision: Union[str, Sequence[str], None] = "g1p2d0000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "offline_operation_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("operation_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=64), nullable=False),
        sa.Column("response_payload", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_offline_operation_logs_created_at",
        "offline_operation_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_offline_operation_logs_idempotency_key",
        "offline_operation_logs",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_offline_operation_logs_operation_type",
        "offline_operation_logs",
        ["operation_type"],
        unique=False,
    )
    op.create_index(
        "ix_offline_operation_logs_user_id",
        "offline_operation_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "uq_offline_operation_logs_user_key",
        "offline_operation_logs",
        ["user_id", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_offline_operation_logs_user_key", table_name="offline_operation_logs")
    op.drop_index("ix_offline_operation_logs_user_id", table_name="offline_operation_logs")
    op.drop_index("ix_offline_operation_logs_operation_type", table_name="offline_operation_logs")
    op.drop_index("ix_offline_operation_logs_idempotency_key", table_name="offline_operation_logs")
    op.drop_index("ix_offline_operation_logs_created_at", table_name="offline_operation_logs")
    op.drop_table("offline_operation_logs")
