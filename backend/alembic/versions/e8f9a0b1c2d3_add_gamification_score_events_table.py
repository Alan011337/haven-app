"""Add gamification_score_events table

Revision ID: e8f9a0b1c2d3
Revises: d7e8f9a0b1c2
Create Date: 2026-02-22 14:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8f9a0b1c2d3"
down_revision: Union[str, Sequence[str], None] = "d7e8f9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gamification_score_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("score_delta", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_gamification_score_events_created_at",
        "gamification_score_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_gamification_score_events_user_id",
        "gamification_score_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_gamification_score_events_journal_id",
        "gamification_score_events",
        ["journal_id"],
        unique=False,
    )
    op.create_index(
        "ix_gamification_score_events_event_type",
        "gamification_score_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_gamification_score_events_event_date",
        "gamification_score_events",
        ["event_date"],
        unique=False,
    )
    op.create_index(
        "ix_gamification_score_events_content_hash",
        "gamification_score_events",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        "uq_gamification_score_events_dedupe_key",
        "gamification_score_events",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_gamification_score_events_user_event_date",
        "gamification_score_events",
        ["user_id", "event_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_gamification_score_events_user_event_date",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "uq_gamification_score_events_dedupe_key",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_content_hash",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_event_date",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_event_type",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_journal_id",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_user_id",
        table_name="gamification_score_events",
    )
    op.drop_index(
        "ix_gamification_score_events_created_at",
        table_name="gamification_score_events",
    )
    op.drop_table("gamification_score_events")
