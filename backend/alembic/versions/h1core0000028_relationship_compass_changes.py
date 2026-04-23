"""Add relationship_compass_changes history table.

Revision ID: h1core0000028
Revises: h1core0000027
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000028"
down_revision: Union[str, Sequence[str], None] = "h1core0000027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_compass_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("identity_statement_before", sa.String(length=500), nullable=True),
        sa.Column("identity_statement_after", sa.String(length=500), nullable=True),
        sa.Column("story_anchor_before", sa.String(length=500), nullable=True),
        sa.Column("story_anchor_after", sa.String(length=500), nullable=True),
        sa.Column("future_direction_before", sa.String(length=500), nullable=True),
        sa.Column("future_direction_after", sa.String(length=500), nullable=True),
        sa.Column("revision_note", sa.String(length=300), nullable=True),
    )
    op.create_index(
        "ix_rcc_pair_changed_at",
        "relationship_compass_changes",
        ["user_id", "partner_id", "changed_at"],
    )
    op.create_index(
        "ix_relationship_compass_changes_user_id",
        "relationship_compass_changes",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_compass_changes_partner_id",
        "relationship_compass_changes",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_compass_changes_changed_by_user_id",
        "relationship_compass_changes",
        ["changed_by_user_id"],
    )
    op.create_index(
        "ix_relationship_compass_changes_changed_at",
        "relationship_compass_changes",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_compass_changes")
