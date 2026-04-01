"""Add relationship_knowledge_suggestions table.

Revision ID: h1core0000019
Revises: h1core0000018
Create Date: 2026-03-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000019"
down_revision: Union[str, Sequence[str], None] = "h1core0000018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "relationship_knowledge_suggestions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("partner_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("section", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("generator_version", sa.String(length=64), nullable=False),
        sa.Column("proposed_title", sa.String(length=500), nullable=False),
        sa.Column("proposed_notes", sa.String(length=2000), nullable=False, server_default=""),
        sa.Column("evidence_json", sa.JSON(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column(
            "accepted_wishlist_item_id",
            sa.Uuid(),
            sa.ForeignKey("wishlist_items.id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_rel_knowledge_suggestions_scope_status",
        "relationship_knowledge_suggestions",
        ["user_id", "partner_id", "section", "status"],
    )
    op.create_index(
        "uq_rel_knowledge_suggestions_scope_dedupe",
        "relationship_knowledge_suggestions",
        ["user_id", "partner_id", "section", "dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_user_id",
        "relationship_knowledge_suggestions",
        ["user_id"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_partner_id",
        "relationship_knowledge_suggestions",
        ["partner_id"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_section",
        "relationship_knowledge_suggestions",
        ["section"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_status",
        "relationship_knowledge_suggestions",
        ["status"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_dedupe_key",
        "relationship_knowledge_suggestions",
        ["dedupe_key"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_created_at",
        "relationship_knowledge_suggestions",
        ["created_at"],
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_reviewed_at",
        "relationship_knowledge_suggestions",
        ["reviewed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_relationship_knowledge_suggestions_reviewed_at",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_created_at",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_dedupe_key",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_status",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_section",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_partner_id",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_relationship_knowledge_suggestions_user_id",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "uq_rel_knowledge_suggestions_scope_dedupe",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_index(
        "ix_rel_knowledge_suggestions_scope_status",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_table("relationship_knowledge_suggestions")
