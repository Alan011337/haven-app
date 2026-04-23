"""Add pair-maintained relationship compass.

Revision ID: h1core0000027
Revises: h1core0000026
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000027"
down_revision: Union[str, Sequence[str], None] = "h1core0000026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_compasses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("identity_statement", sa.String(length=500), nullable=True),
        sa.Column("story_anchor", sa.String(length=500), nullable=True),
        sa.Column("future_direction", sa.String(length=500), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_relationship_compasses_scope",
        "relationship_compasses",
        ["user_id", "partner_id"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_compasses_user_id",
        "relationship_compasses",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_compasses_partner_id",
        "relationship_compasses",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_compasses_updated_by_user_id",
        "relationship_compasses",
        ["updated_by_user_id"],
    )
    op.create_index(
        "ix_relationship_compasses_updated_at",
        "relationship_compasses",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_compasses")
