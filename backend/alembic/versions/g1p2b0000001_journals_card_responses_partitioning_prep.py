"""P2-B: Partitioning design for journals and card_responses (prep)

Revision ID: g1p2b0000001
Revises: f2b3c4d5e6f7
Create Date: 2026-02-23

Partitioning strategy: see docs/backend/partitioning-strategy.md.
This migration only adds table comments to document intent; actual partition
creation is manual or via ENABLE_PARTITIONING=1 in a future migration.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "g1p2b0000001"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    dialect_name = conn.dialect.name
    if dialect_name != "postgresql":
        return
    op.execute(
        "COMMENT ON TABLE journals IS 'P2-B: Partitioning by RANGE(created_at) planned; see docs/backend/partitioning-strategy.md'"
    )
    op.execute(
        "COMMENT ON TABLE card_responses IS 'P2-B: Partitioning by RANGE(created_at) planned; see docs/backend/partitioning-strategy.md'"
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.execute("COMMENT ON TABLE journals IS NULL")
    op.execute("COMMENT ON TABLE card_responses IS NULL")
