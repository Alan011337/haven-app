"""Add tie-break composite indexes for timeline cursor pagination.

Revision ID: h1core0000011
Revises: h1core0000010
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op


revision: str = "h1core0000011"
down_revision: Union[str, Sequence[str], None] = "h1core0000010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Cursor tie-break optimization:
    # WHERE (created_at < ts) OR (created_at = ts AND id < cursor_id)
    # plus deleted_at/user filters on timeline paths.
    op.create_index(
        "ix_journals_user_deleted_created_id",
        "journals",
        ["user_id", "deleted_at", "created_at", "id"],
    )
    op.create_index(
        "ix_card_sessions_creator_deleted_created_id",
        "card_sessions",
        ["creator_id", "deleted_at", "created_at", "id"],
    )
    op.create_index(
        "ix_card_sessions_partner_deleted_created_id",
        "card_sessions",
        ["partner_id", "deleted_at", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_card_sessions_partner_deleted_created_id",
        table_name="card_sessions",
    )
    op.drop_index(
        "ix_card_sessions_creator_deleted_created_id",
        table_name="card_sessions",
    )
    op.drop_index(
        "ix_journals_user_deleted_created_id",
        table_name="journals",
    )
