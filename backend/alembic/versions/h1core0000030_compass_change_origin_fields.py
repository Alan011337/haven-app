"""Add origin marker for Compass history rows.

Revision ID: h1core0000030
Revises: h1core0000029
Create Date: 2026-04-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000030"
down_revision: Union[str, Sequence[str], None] = "h1core0000029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relationship_compass_changes",
        sa.Column(
            "origin_kind",
            sa.String(length=32),
            nullable=False,
            server_default="manual_edit",
        ),
    )
    op.add_column(
        "relationship_compass_changes",
        sa.Column(
            "source_suggestion_id",
            sa.Uuid(),
            sa.ForeignKey("relationship_knowledge_suggestions.id"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("relationship_compass_changes", "source_suggestion_id")
    op.drop_column("relationship_compass_changes", "origin_kind")

