"""Add Journal draft state flag.

Revision ID: h1core0000018
Revises: h1core0000017
Create Date: 2026-03-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000018"
down_revision: Union[str, Sequence[str], None] = "h1core0000017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "journals",
        sa.Column(
            "is_draft",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("journals", "is_draft")
