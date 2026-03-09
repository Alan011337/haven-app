"""add card query indexes

Revision ID: b8f2c8a7d4e1
Revises: a7cd980a6ab0
Create Date: 2026-02-15 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b8f2c8a7d4e1"
down_revision: Union[str, Sequence[str], None] = "a7cd980a6ab0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_responses_user_id ON card_responses (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_responses_card_id ON card_responses (card_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_responses_session_id ON card_responses (session_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_sessions_creator_created_at ON card_sessions (creator_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_sessions_partner_created_at ON card_sessions (partner_id, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_card_sessions_status_created_at ON card_sessions (status, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cards_deck_id ON cards (deck_id)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_cards_deck_id")
    op.execute("DROP INDEX IF EXISTS ix_card_sessions_status_created_at")
    op.execute("DROP INDEX IF EXISTS ix_card_sessions_partner_created_at")
    op.execute("DROP INDEX IF EXISTS ix_card_sessions_creator_created_at")
    op.execute("DROP INDEX IF EXISTS ix_card_responses_session_id")
    op.execute("DROP INDEX IF EXISTS ix_card_responses_card_id")
    op.execute("DROP INDEX IF EXISTS ix_card_responses_user_id")
