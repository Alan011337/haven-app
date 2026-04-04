"""Add partner_translation_ready_at to journals.

Revision ID: h1core0000021
Revises: h1core0000020
Create Date: 2026-04-04

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000021"
down_revision: Union[str, Sequence[str], None] = "h1core0000020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "journals",
        sa.Column("partner_translation_ready_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("journals", "partner_translation_ready_at")
