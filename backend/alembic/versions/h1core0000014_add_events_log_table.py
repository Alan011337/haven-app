"""Add events_log table for core-loop telemetry.

Revision ID: h1core0000014
Revises: h1core0000013
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000014"
down_revision: Union[str, Sequence[str], None] = "h1core0000013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "events_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("partner_user_id", sa.Uuid(), nullable=True),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("event_id", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("session_id", sa.String(length=128), nullable=True),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("props_json", sa.String(length=2000), nullable=True),
        sa.Column("context_json", sa.String(length=2000), nullable=True),
        sa.Column("privacy_json", sa.String(length=2000), nullable=True),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["partner_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_log_created_at", "events_log", ["created_at"], unique=False)
    op.create_index("ix_events_log_updated_at", "events_log", ["updated_at"], unique=False)
    op.create_index("ix_events_log_ts", "events_log", ["ts"], unique=False)
    op.create_index("ix_events_log_user_id", "events_log", ["user_id"], unique=False)
    op.create_index("ix_events_log_partner_user_id", "events_log", ["partner_user_id"], unique=False)
    op.create_index("ix_events_log_event_name", "events_log", ["event_name"], unique=False)
    op.create_index("ix_events_log_event_id", "events_log", ["event_id"], unique=False)
    op.create_index("ix_events_log_source", "events_log", ["source"], unique=False)
    op.create_index("ix_events_log_session_id", "events_log", ["session_id"], unique=False)
    op.create_index("ix_events_log_device_id", "events_log", ["device_id"], unique=False)
    op.create_index("uq_events_log_dedupe_key", "events_log", ["dedupe_key"], unique=True)
    op.create_index(
        "ix_events_log_user_event_ts",
        "events_log",
        ["user_id", "event_name", "ts"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_partner_event_ts",
        "events_log",
        ["partner_user_id", "event_name", "ts"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_events_log_partner_event_ts", table_name="events_log")
    op.drop_index("ix_events_log_user_event_ts", table_name="events_log")
    op.drop_index("uq_events_log_dedupe_key", table_name="events_log")
    op.drop_index("ix_events_log_device_id", table_name="events_log")
    op.drop_index("ix_events_log_session_id", table_name="events_log")
    op.drop_index("ix_events_log_source", table_name="events_log")
    op.drop_index("ix_events_log_event_id", table_name="events_log")
    op.drop_index("ix_events_log_event_name", table_name="events_log")
    op.drop_index("ix_events_log_partner_user_id", table_name="events_log")
    op.drop_index("ix_events_log_user_id", table_name="events_log")
    op.drop_index("ix_events_log_ts", table_name="events_log")
    op.drop_index("ix_events_log_updated_at", table_name="events_log")
    op.drop_index("ix_events_log_created_at", table_name="events_log")
    op.drop_table("events_log")
