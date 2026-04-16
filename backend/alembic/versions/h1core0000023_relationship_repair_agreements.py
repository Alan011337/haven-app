"""Add relationship_repair_agreements table for pair-maintained repair norms.

Revision ID: h1core0000023
Revises: h1core0000022
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000023"
down_revision: Union[str, Sequence[str], None] = "h1core0000022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_repair_agreements",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("protect_what_matters", sa.String(length=500), nullable=True),
        sa.Column("avoid_in_conflict", sa.String(length=500), nullable=True),
        sa.Column("repair_reentry", sa.String(length=500), nullable=True),
        sa.Column("updated_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_relationship_repair_agreements_scope",
        "relationship_repair_agreements",
        ["user_id", "partner_id"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_repair_agreements_user_id",
        "relationship_repair_agreements",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreements_partner_id",
        "relationship_repair_agreements",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreements_updated_by_user_id",
        "relationship_repair_agreements",
        ["updated_by_user_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreements_updated_at",
        "relationship_repair_agreements",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_repair_agreements")
