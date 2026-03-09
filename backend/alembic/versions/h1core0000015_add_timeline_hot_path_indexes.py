"""Add timeline hot-path indexes for cursor pagination.

Revision ID: h1core0000015
Revises: h1core0000014
Create Date: 2026-03-02
"""

from typing import Sequence, Union

from alembic import op


revision: str = "h1core0000015"
down_revision: Union[str, Sequence[str], None] = "h1core0000014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Timeline card-session hot path:
    #   mode/status constant filters + actor filter + soft-delete + cursor sort.
    op.create_index(
        "ix_card_sessions_mode_status_creator_deleted_created_id",
        "card_sessions",
        ["mode", "status", "creator_id", "deleted_at", "created_at", "id"],
    )
    op.create_index(
        "ix_card_sessions_mode_status_partner_deleted_created_id",
        "card_sessions",
        ["mode", "status", "partner_id", "deleted_at", "created_at", "id"],
    )

    # Timeline response hydration hot path:
    #   session IN (...) + deleted_at is null + per-user lookup.
    op.create_index(
        "ix_card_responses_session_deleted_user",
        "card_responses",
        ["session_id", "deleted_at", "user_id"],
    )


def downgrade() -> None:
    # Use IF EXISTS to stay rollback-safe in stamped bootstrap environments.
    op.execute("DROP INDEX IF EXISTS ix_card_responses_session_deleted_user")
    op.execute("DROP INDEX IF EXISTS ix_card_sessions_mode_status_partner_deleted_created_id")
    op.execute("DROP INDEX IF EXISTS ix_card_sessions_mode_status_creator_deleted_created_id")
