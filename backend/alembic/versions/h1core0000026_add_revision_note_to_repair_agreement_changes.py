"""Add revision_note column to relationship_repair_agreement_changes.

Optional short human-authored note attached to a Repair Agreements change row.
Never mandatory, never AI-generated. Max 300 chars matches the existing
`improvement_note` cap on `relationship_repair_outcome_captures` to avoid
introducing a third short-text length across the codebase.

Revision ID: h1core0000026
Revises: h1core0000025
Create Date: 2026-04-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000026"
down_revision: Union[str, Sequence[str], None] = "h1core0000025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relationship_repair_agreement_changes",
        sa.Column("revision_note", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relationship_repair_agreement_changes", "revision_note")
