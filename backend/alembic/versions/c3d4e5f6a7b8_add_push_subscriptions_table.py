"""Add push_subscriptions table

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-22 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(), nullable=True),
        sa.Column("dry_run_sampled_at", sa.DateTime(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("endpoint", sa.String(length=2048), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("p256dh_key", sa.String(length=512), nullable=False),
        sa.Column("auth_key", sa.String(length=512), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("expiration_time", sa.DateTime(), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("fail_reason", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_push_subscriptions_created_at", "push_subscriptions", ["created_at"], unique=False)
    op.create_index("ix_push_subscriptions_updated_at", "push_subscriptions", ["updated_at"], unique=False)
    op.create_index(
        "ix_push_subscriptions_last_success_at",
        "push_subscriptions",
        ["last_success_at"],
        unique=False,
    )
    op.create_index(
        "ix_push_subscriptions_last_failure_at",
        "push_subscriptions",
        ["last_failure_at"],
        unique=False,
    )
    op.create_index(
        "ix_push_subscriptions_dry_run_sampled_at",
        "push_subscriptions",
        ["dry_run_sampled_at"],
        unique=False,
    )
    op.create_index("ix_push_subscriptions_deleted_at", "push_subscriptions", ["deleted_at"], unique=False)
    op.create_index("ix_push_subscriptions_user_id", "push_subscriptions", ["user_id"], unique=False)
    op.create_index("ix_push_subscriptions_endpoint_hash", "push_subscriptions", ["endpoint_hash"], unique=False)
    op.create_index("ix_push_subscriptions_state", "push_subscriptions", ["state"], unique=False)
    op.create_index("uq_push_subscriptions_endpoint", "push_subscriptions", ["endpoint"], unique=True)
    op.create_index(
        "ix_push_subscriptions_user_state",
        "push_subscriptions",
        ["user_id", "state"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_push_subscriptions_user_state", table_name="push_subscriptions")
    op.drop_index("uq_push_subscriptions_endpoint", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_state", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_endpoint_hash", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_user_id", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_deleted_at", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_dry_run_sampled_at", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_last_failure_at", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_last_success_at", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_updated_at", table_name="push_subscriptions")
    op.drop_index("ix_push_subscriptions_created_at", table_name="push_subscriptions")
    op.drop_table("push_subscriptions")

