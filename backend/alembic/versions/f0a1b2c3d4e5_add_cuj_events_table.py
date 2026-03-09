"""Add cuj_events table

Revision ID: f0a1b2c3d4e5
Revises: e8f9a0b1c2d3
Create Date: 2026-02-22 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "e8f9a0b1c2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cuj_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("partner_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.String(length=2000), nullable=True),
        sa.ForeignKeyConstraint(["partner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cuj_events_created_at", "cuj_events", ["created_at"], unique=False)
    op.create_index("ix_cuj_events_updated_at", "cuj_events", ["updated_at"], unique=False)
    op.create_index("ix_cuj_events_occurred_at", "cuj_events", ["occurred_at"], unique=False)
    op.create_index("ix_cuj_events_user_id", "cuj_events", ["user_id"], unique=False)
    op.create_index("ix_cuj_events_partner_user_id", "cuj_events", ["partner_user_id"], unique=False)
    op.create_index("ix_cuj_events_event_name", "cuj_events", ["event_name"], unique=False)
    op.create_index("ix_cuj_events_event_id", "cuj_events", ["event_id"], unique=False)
    op.create_index("ix_cuj_events_source", "cuj_events", ["source"], unique=False)
    op.create_index("ix_cuj_events_mode", "cuj_events", ["mode"], unique=False)
    op.create_index("ix_cuj_events_session_id", "cuj_events", ["session_id"], unique=False)
    op.create_index("ix_cuj_events_request_id", "cuj_events", ["request_id"], unique=False)
    op.create_index("uq_cuj_events_dedupe_key", "cuj_events", ["dedupe_key"], unique=True)
    op.create_index(
        "ix_cuj_events_user_event_created",
        "cuj_events",
        ["user_id", "event_name", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cuj_events_user_event_created", table_name="cuj_events")
    op.drop_index("uq_cuj_events_dedupe_key", table_name="cuj_events")
    op.drop_index("ix_cuj_events_request_id", table_name="cuj_events")
    op.drop_index("ix_cuj_events_session_id", table_name="cuj_events")
    op.drop_index("ix_cuj_events_mode", table_name="cuj_events")
    op.drop_index("ix_cuj_events_source", table_name="cuj_events")
    op.drop_index("ix_cuj_events_event_id", table_name="cuj_events")
    op.drop_index("ix_cuj_events_event_name", table_name="cuj_events")
    op.drop_index("ix_cuj_events_partner_user_id", table_name="cuj_events")
    op.drop_index("ix_cuj_events_user_id", table_name="cuj_events")
    op.drop_index("ix_cuj_events_occurred_at", table_name="cuj_events")
    op.drop_index("ix_cuj_events_updated_at", table_name="cuj_events")
    op.drop_index("ix_cuj_events_created_at", table_name="cuj_events")
    op.drop_table("cuj_events")
