"""Add daily_sync table (Module B1).

Revision ID: h1core0000003
Revises: h1core0000002
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000003"
down_revision: Union[str, Sequence[str], None] = "h1core0000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_sync",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("sync_date", sa.Date(), nullable=False),
        sa.Column("mood_score", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=64), nullable=False),
        sa.Column("answer_text", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_daily_sync_user_id", "daily_sync", ["user_id"])
    op.create_index("ix_daily_sync_sync_date", "daily_sync", ["sync_date"])
    op.create_index("uq_daily_sync_user_date", "daily_sync", ["user_id", "sync_date"], unique=True)


def downgrade() -> None:
    op.drop_table("daily_sync")
