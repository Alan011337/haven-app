"""P2-D: Active Care, Conflict Mediation, Legacy Contact

Revision ID: g1p2d0000001
Revises: g1p2b0000002
Create Date: 2026-02-23

- analyses.conflict_risk_detected (bool) for conflict resolution
- mediation_sessions for conflict mediation flow
- users.legacy_contact_email for LEGAL-02 Legacy Contact
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g1p2d0000001"
down_revision: Union[str, Sequence[str], None] = "g1p2b0000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "analyses",
        sa.Column("conflict_risk_detected", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.create_table(
        "mediation_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id_1", sa.Uuid(), nullable=False),
        sa.Column("user_id_2", sa.Uuid(), nullable=False),
        sa.Column("triggered_by_journal_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_1_answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_2_answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id_1"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id_2"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_journal_id"], ["journals.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_mediation_sessions_user_id_1_user_id_2",
        "mediation_sessions",
        ["user_id_1", "user_id_2"],
        unique=False,
    )
    op.add_column(
        "users",
        sa.Column("legacy_contact_email", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "legacy_contact_email")
    op.drop_index("ix_mediation_sessions_user_id_1_user_id_2", table_name="mediation_sessions")
    op.drop_table("mediation_sessions")
    op.drop_column("analyses", "conflict_risk_detected")
