"""DATA-READ-01: Precomputed streak summary read model

Revision ID: g1p2b0000002
Revises: g1p2b0000001
Create Date: 2026-02-23

Adds user_streak_summary table for read path: gamification summary can be served
from this table when fresh; otherwise compute and upsert.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g1p2b0000002"
down_revision: Union[str, Sequence[str], None] = "g1p2b0000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_streak_summary",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("has_partner_context", sa.Boolean(), nullable=False),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("best_streak_days", sa.Integer(), nullable=False),
        sa.Column("streak_eligible_today", sa.Boolean(), nullable=False),
        sa.Column("level", sa.Integer(), nullable=False),
        sa.Column("level_points_total", sa.Integer(), nullable=False),
        sa.Column("level_points_current", sa.Integer(), nullable=False),
        sa.Column("level_points_target", sa.Integer(), nullable=False),
        sa.Column("love_bar_percent", sa.Float(), nullable=False),
        sa.Column("level_title", sa.String(length=64), nullable=False),
        sa.Column("anti_cheat_enabled", sa.Boolean(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("user_id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(
        "ix_user_streak_summary_updated_at",
        "user_streak_summary",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_user_streak_summary_updated_at", table_name="user_streak_summary")
    op.drop_table("user_streak_summary")
