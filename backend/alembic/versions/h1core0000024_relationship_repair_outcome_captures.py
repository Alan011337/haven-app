"""Add relationship_repair_outcome_captures for reviewed post-mediation carry-forward drafts.

Revision ID: h1core0000024
Revises: h1core0000023
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000024"
down_revision: Union[str, Sequence[str], None] = "h1core0000023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_repair_outcome_captures",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("repair_session_id", sa.String(length=128), nullable=False),
        sa.Column("shared_commitment", sa.String(length=300), nullable=True),
        sa.Column("improvement_note", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="collecting"),
        sa.Column("created_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "uq_relationship_repair_outcome_captures_session_id",
        "relationship_repair_outcome_captures",
        ["repair_session_id"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_pair_status",
        "relationship_repair_outcome_captures",
        ["user_id", "partner_id", "status"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_user_id",
        "relationship_repair_outcome_captures",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_partner_id",
        "relationship_repair_outcome_captures",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_repair_session_id",
        "relationship_repair_outcome_captures",
        ["repair_session_id"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_status",
        "relationship_repair_outcome_captures",
        ["status"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_created_by_user_id",
        "relationship_repair_outcome_captures",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_reviewed_by_user_id",
        "relationship_repair_outcome_captures",
        ["reviewed_by_user_id"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_updated_at",
        "relationship_repair_outcome_captures",
        ["updated_at"],
    )
    op.create_index(
        "ix_relationship_repair_outcome_captures_reviewed_at",
        "relationship_repair_outcome_captures",
        ["reviewed_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_repair_outcome_captures")
