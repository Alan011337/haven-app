"""Add relationship_baseline and couple_goal tables (Module A2).

Revision ID: h1core0000002
Revises: h1core0000001
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000002"
down_revision: Union[str, Sequence[str], None] = "h1core0000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_baseline",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("filled_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("scores", sa.JSON(), nullable=False),
    )
    op.create_index("ix_relationship_baseline_user_id", "relationship_baseline", ["user_id"], unique=True)
    op.create_index("ix_relationship_baseline_partner_id", "relationship_baseline", ["partner_id"])

    op.create_table(
        "couple_goal",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("goal_slug", sa.String(length=64), nullable=False),
        sa.Column("chosen_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_couple_goal_user_id", "couple_goal", ["user_id"])
    op.create_index("ix_couple_goal_partner_id", "couple_goal", ["partner_id"])
    op.create_index("ix_couple_goal_goal_slug", "couple_goal", ["goal_slug"])
    # One row per couple (canonical pair): ensure we can look up by (min_id, max_id)
    op.create_index(
        "uq_couple_goal_pair",
        "couple_goal",
        ["user_id", "partner_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("couple_goal")
    op.drop_table("relationship_baseline")
