"""Add structured candidate payload to relationship suggestions.

Revision ID: h1core0000029
Revises: h1core0000028
Create Date: 2026-04-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000029"
down_revision: Union[str, Sequence[str], None] = "h1core0000028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relationship_knowledge_suggestions",
        sa.Column("candidate_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("relationship_knowledge_suggestions", "candidate_json")
