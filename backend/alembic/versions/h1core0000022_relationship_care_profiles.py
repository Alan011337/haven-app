"""Add relationship_care_profiles table for Heart Care Playbook.

Revision ID: h1core0000022
Revises: h1core0000021
Create Date: 2026-04-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000022"
down_revision: Union[str, Sequence[str], None] = "h1core0000021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_care_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("support_me", sa.String(length=500), nullable=True),
        sa.Column("avoid_when_stressed", sa.String(length=500), nullable=True),
        sa.Column("small_delights", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "uq_relationship_care_profiles_scope",
        "relationship_care_profiles",
        ["user_id", "partner_id"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_care_profiles_user_id",
        "relationship_care_profiles",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_care_profiles_partner_id",
        "relationship_care_profiles",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_care_profiles_updated_at",
        "relationship_care_profiles",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_care_profiles")
