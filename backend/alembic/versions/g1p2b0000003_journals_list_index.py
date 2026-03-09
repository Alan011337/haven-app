"""Add composite index on journals (user_id, created_at DESC) for list queries.

Revision ID: g1p2b0000003
Revises: g1p2i0000001
Create Date: 2026-02-23

Speeds up GET /journals/ and GET /journals/partner (ORDER BY created_at DESC).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "g1p2b0000003"
down_revision: Union[str, Sequence[str], None] = "g1p2i0000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.create_index(
        "ix_journals_user_id_created_at_desc",
        "journals",
        ["user_id", sa.text("created_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return
    op.drop_index("ix_journals_user_id_created_at_desc", table_name="journals")
