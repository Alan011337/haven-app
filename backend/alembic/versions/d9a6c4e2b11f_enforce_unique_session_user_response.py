"""Enforce unique response per (session_id, user_id)

Revision ID: d9a6c4e2b11f
Revises: c6f2d9f4c1ab
Create Date: 2026-02-15 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d9a6c4e2b11f"
down_revision: Union[str, Sequence[str], None] = "c6f2d9f4c1ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Keep the newest row and remove older duplicates before adding uniqueness.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id, user_id
                    ORDER BY created_at DESC, id DESC
                ) AS rn
            FROM card_responses
            WHERE session_id IS NOT NULL
        )
        DELETE FROM card_responses
        WHERE id IN (
            SELECT id FROM ranked WHERE rn > 1
        )
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_card_responses_session_id")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_card_responses_session_user "
        "ON card_responses (session_id, user_id)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS uq_card_responses_session_user")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_card_responses_session_id "
        "ON card_responses (session_id)"
    )
