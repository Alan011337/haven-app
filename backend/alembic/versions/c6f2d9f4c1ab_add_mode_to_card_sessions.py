"""Add mode to card_sessions

Revision ID: c6f2d9f4c1ab
Revises: b8f2c8a7d4e1
Create Date: 2026-02-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c6f2d9f4c1ab"
down_revision: Union[str, Sequence[str], None] = "b8f2c8a7d4e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "card_sessions",
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="DECK"),
    )
    op.create_check_constraint(
        "ck_card_sessions_mode_valid",
        "card_sessions",
        "mode IN ('DAILY_RITUAL', 'DECK')",
    )
    op.create_index(
        "ix_card_sessions_mode_created_at",
        "card_sessions",
        ["mode", "created_at"],
        unique=False,
    )
    op.alter_column("card_sessions", "mode", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_card_sessions_mode_created_at", table_name="card_sessions")
    op.drop_constraint("ck_card_sessions_mode_valid", "card_sessions", type_="check")
    op.drop_column("card_sessions", "mode")
