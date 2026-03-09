"""Add cool_down_session table (Module C1).

Revision ID: h1core0000006
Revises: h1core0000005
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000006"
down_revision: Union[str, Sequence[str], None] = "h1core0000005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cool_down_session",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("state", sa.String(length=16), nullable=False, server_default="active"),
    )
    op.create_index("ix_cool_down_session_user_id", "cool_down_session", ["user_id"])
    op.create_index("ix_cool_down_session_partner_id", "cool_down_session", ["partner_id"])
    op.create_index("ix_cool_down_session_ends_at", "cool_down_session", ["ends_at"])
    op.create_index("ix_cool_down_session_state", "cool_down_session", ["state"])


def downgrade() -> None:
    op.drop_table("cool_down_session")
