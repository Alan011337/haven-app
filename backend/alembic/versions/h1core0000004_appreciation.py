"""Add appreciation table (Module B2).

Revision ID: h1core0000004
Revises: h1core0000003
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000004"
down_revision: Union[str, Sequence[str], None] = "h1core0000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "appreciation",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body_text", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_appreciation_user_id", "appreciation", ["user_id"])
    op.create_index("ix_appreciation_partner_id", "appreciation", ["partner_id"])
    op.create_index("ix_appreciation_created_at", "appreciation", ["created_at"])


def downgrade() -> None:
    op.drop_table("appreciation")
