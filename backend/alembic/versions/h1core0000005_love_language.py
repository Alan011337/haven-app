"""Add love_language_preference and love_language_task_assignment (Module B3).

Revision ID: h1core0000005
Revises: h1core0000004
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000005"
down_revision: Union[str, Sequence[str], None] = "h1core0000004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "love_language_preference",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preference", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_table(
        "love_language_task_assignment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("task_slug", sa.String(length=128), nullable=False),
        sa.Column("assigned_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_love_language_task_assignment_user_id", "love_language_task_assignment", ["user_id"])
    op.create_index("ix_love_language_task_assignment_partner_id", "love_language_task_assignment", ["partner_id"])
    op.create_index("ix_love_language_task_assignment_task_slug", "love_language_task_assignment", ["task_slug"])


def downgrade() -> None:
    op.drop_table("love_language_task_assignment")
    op.drop_table("love_language_preference")
