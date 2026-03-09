"""Add mediation_answers table (Module C3).

Revision ID: h1core0000007
Revises: h1core0000006
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000007"
down_revision: Union[str, Sequence[str], None] = "h1core0000006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mediation_answers",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mediation_session_id", sa.Uuid(), sa.ForeignKey("mediation_sessions.id"), nullable=False),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("answer_1", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("answer_2", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("answer_3", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_mediation_answers_mediation_session_id", "mediation_answers", ["mediation_session_id"])
    op.create_index("ix_mediation_answers_user_id", "mediation_answers", ["user_id"])


def downgrade() -> None:
    op.drop_table("mediation_answers")
