"""Enforce notification dedupe uniqueness per receiver email

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-02-16 17:10:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep newest row per (receiver_email, dedupe_key) and remove older duplicates.
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY receiver_email, dedupe_key
                    ORDER BY created_at DESC, id DESC
                ) AS rn
            FROM notification_events
            WHERE dedupe_key IS NOT NULL
        )
        DELETE FROM notification_events
        WHERE id IN (
            SELECT id FROM ranked WHERE rn > 1
        )
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_events_receiver_email_dedupe
        ON notification_events (receiver_email, dedupe_key)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_notification_events_receiver_email_dedupe")
