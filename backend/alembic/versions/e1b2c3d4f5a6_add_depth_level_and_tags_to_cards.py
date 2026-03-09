"""Add depth_level and tags to cards

Revision ID: e1b2c3d4f5a6
Revises: d9a6c4e2b11f
Create Date: 2026-02-15 16:20:00.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e1b2c3d4f5a6"
down_revision: Union[str, Sequence[str], None] = "d9a6c4e2b11f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE cards
        ADD COLUMN IF NOT EXISTS depth_level INTEGER NOT NULL DEFAULT 1
        """
    )
    op.execute(
        """
        ALTER TABLE cards
        ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE cards DROP COLUMN IF EXISTS tags")
    op.execute("ALTER TABLE cards DROP COLUMN IF EXISTS depth_level")
