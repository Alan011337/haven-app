"""Add composite indexes for timeline queries (P2-C optimizations).

This migration adds indexes to support efficient cursor-based pagination
on the unified timeline (journals + card_sessions) and avoids N+1 queries:

- journals(user_id, created_at, deleted_at): for soft-deleted timeline queries
- card_sessions(creator_id, created_at, deleted_at): for soft-deleted timeline queries
- card_sessions(partner_id, created_at, deleted_at): for paired timeline queries
- card_responses(session_id, user_id): for efficient card response lookups during pagination

Revision ID: h1core0000010
Revises: h1core0000009
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op


revision: str = "h1core0000010"
down_revision: Union[str, Sequence[str], None] = "h1core0000009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Timeline query optimization: journals soft-deleted lookups
    # Index: (user_id, created_at DESC, deleted_at) for efficient filtering
    op.create_index(
        "ix_journals_user_id_created_at_deleted_at",
        "journals",
        ["user_id", "created_at", "deleted_at"],
        postgresql_using="btree",
    )

    # Timeline query optimization: card_sessions creator-side timeline
    # Includes deleted_at for soft-delete filtering
    op.create_index(
        "ix_card_sessions_creator_id_created_at_deleted_at",
        "card_sessions",
        ["creator_id", "created_at", "deleted_at"],
        postgresql_using="btree",
    )

    # Timeline query optimization: card_sessions partner-side timeline
    op.create_index(
        "ix_card_sessions_partner_id_created_at_deleted_at",
        "card_sessions",
        ["partner_id", "created_at", "deleted_at"],
        postgresql_using="btree",
    )

    # Pagination helper: efficient card_response lookups during timeline aggregation
    # Avoids N+1 when fetching responses for multiple sessions
    op.create_index(
        "ix_card_responses_session_id_user_id",
        "card_responses",
        ["session_id", "user_id"],
        postgresql_using="btree",
    )


def downgrade() -> None:
    op.drop_index("ix_card_responses_session_id_user_id", table_name="card_responses")
    op.drop_index(
        "ix_card_sessions_partner_id_created_at_deleted_at",
        table_name="card_sessions",
    )
    op.drop_index(
        "ix_card_sessions_creator_id_created_at_deleted_at",
        table_name="card_sessions",
    )
    op.drop_index(
        "ix_journals_user_id_created_at_deleted_at", table_name="journals"
    )
