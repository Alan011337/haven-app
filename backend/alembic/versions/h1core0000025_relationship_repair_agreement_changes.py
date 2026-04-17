"""Add relationship_repair_agreement_changes for lightweight Repair Agreements history.

Revision ID: h1core0000025
Revises: h1core0000024
Create Date: 2026-04-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000025"
down_revision: Union[str, Sequence[str], None] = "h1core0000024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_repair_agreement_changes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "repair_agreement_id",
            sa.Uuid(),
            sa.ForeignKey("relationship_repair_agreements.id"),
            nullable=False,
        ),
        sa.Column("changed_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("origin_kind", sa.String(length=64), nullable=False),
        sa.Column(
            "source_outcome_capture_id",
            sa.Uuid(),
            sa.ForeignKey("relationship_repair_outcome_captures.id"),
            nullable=True,
        ),
        sa.Column("source_captured_by_user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("source_captured_at", sa.DateTime(), nullable=True),
        sa.Column("changed_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("protect_what_matters_before", sa.String(length=500), nullable=True),
        sa.Column("protect_what_matters_after", sa.String(length=500), nullable=True),
        sa.Column("avoid_in_conflict_before", sa.String(length=500), nullable=True),
        sa.Column("avoid_in_conflict_after", sa.String(length=500), nullable=True),
        sa.Column("repair_reentry_before", sa.String(length=500), nullable=True),
        sa.Column("repair_reentry_after", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_pair_changed_at",
        "relationship_repair_agreement_changes",
        ["user_id", "partner_id", "changed_at"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_user_id",
        "relationship_repair_agreement_changes",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_partner_id",
        "relationship_repair_agreement_changes",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_repair_agreement_id",
        "relationship_repair_agreement_changes",
        ["repair_agreement_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_changed_by_user_id",
        "relationship_repair_agreement_changes",
        ["changed_by_user_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_origin_kind",
        "relationship_repair_agreement_changes",
        ["origin_kind"],
    )
    # Short `ix_rrac_` prefix avoids exceeding Postgres's 63-char identifier limit
    # (default `ix_relationship_repair_agreement_changes_source_outcome_capture_id` = 66 chars).
    op.create_index(
        "ix_rrac_source_outcome_capture_id",
        "relationship_repair_agreement_changes",
        ["source_outcome_capture_id"],
    )
    op.create_index(
        "ix_rrac_source_captured_by_user_id",
        "relationship_repair_agreement_changes",
        ["source_captured_by_user_id"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_source_captured_at",
        "relationship_repair_agreement_changes",
        ["source_captured_at"],
    )
    op.create_index(
        "ix_relationship_repair_agreement_changes_changed_at",
        "relationship_repair_agreement_changes",
        ["changed_at"],
    )


def downgrade() -> None:
    op.drop_table("relationship_repair_agreement_changes")
