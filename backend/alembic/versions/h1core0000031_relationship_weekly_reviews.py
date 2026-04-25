"""Add relationship_weekly_reviews for Relationship System weekly ritual.

Revision ID: h1core0000031
Revises: h1core0000030
Create Date: 2026-04-25

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000031"
down_revision: Union[str, Sequence[str], None] = "h1core0000030"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_weekly_reviews",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user1_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("user2_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("user1_understood", sa.String(length=2000), nullable=True),
        sa.Column("user1_worth", sa.String(length=2000), nullable=True),
        sa.Column("user1_needs_care", sa.String(length=2000), nullable=True),
        sa.Column("user1_next_week", sa.String(length=2000), nullable=True),
        sa.Column("user1_updated_at", sa.DateTime(), nullable=True),
        sa.Column("user2_understood", sa.String(length=2000), nullable=True),
        sa.Column("user2_worth", sa.String(length=2000), nullable=True),
        sa.Column("user2_needs_care", sa.String(length=2000), nullable=True),
        sa.Column("user2_next_week", sa.String(length=2000), nullable=True),
        sa.Column("user2_updated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    op.create_index(
        "uq_relationship_weekly_reviews_scope",
        "relationship_weekly_reviews",
        ["user1_id", "user2_id", "week_start"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_weekly_reviews_pair_week",
        "relationship_weekly_reviews",
        ["user1_id", "user2_id", "week_start"],
    )
    op.create_index(
        "ix_relationship_weekly_reviews_user1_id",
        "relationship_weekly_reviews",
        ["user1_id"],
    )
    op.create_index(
        "ix_relationship_weekly_reviews_user2_id",
        "relationship_weekly_reviews",
        ["user2_id"],
    )
    op.create_index(
        "ix_relationship_weekly_reviews_week_start",
        "relationship_weekly_reviews",
        ["week_start"],
    )
    op.create_index(
        "ix_relationship_weekly_reviews_updated_at",
        "relationship_weekly_reviews",
        ["updated_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_weekly_reviews")

