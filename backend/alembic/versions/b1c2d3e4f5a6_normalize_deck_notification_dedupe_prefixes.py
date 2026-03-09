"""Normalize legacy deck notification dedupe prefixes to card prefixes

Revision ID: b1c2d3e4f5a6
Revises: f4c1d2e3a4b5
Create Date: 2026-02-16 15:40:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "f4c1d2e3a4b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE notification_events
        SET dedupe_key = REPLACE(dedupe_key, 'deck_revealed:', 'card_revealed:')
        WHERE dedupe_key LIKE 'deck_revealed:%'
        """
    )
    op.execute(
        """
        UPDATE notification_events
        SET dedupe_key = REPLACE(dedupe_key, 'deck_waiting:', 'card_waiting:')
        WHERE dedupe_key LIKE 'deck_waiting:%'
        """
    )


def downgrade() -> None:
    # Irreversible data migration:
    # after normalization, historical deck-derived rows are intentionally
    # indistinguishable from card-derived rows.
    pass
