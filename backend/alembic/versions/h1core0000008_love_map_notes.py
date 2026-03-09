"""Add love_map_notes table (Module D1).

Revision ID: h1core0000008
Revises: h1core0000007
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000008"
down_revision: Union[str, Sequence[str], None] = "h1core0000007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "love_map_notes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("layer", sa.String(length=16), nullable=False),
        sa.Column("content", sa.String(length=5000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_love_map_notes_user_id", "love_map_notes", ["user_id"])
    op.create_index("ix_love_map_notes_partner_id", "love_map_notes", ["partner_id"])
    op.create_index("ix_love_map_notes_layer", "love_map_notes", ["layer"])


def downgrade() -> None:
    op.drop_table("love_map_notes")
