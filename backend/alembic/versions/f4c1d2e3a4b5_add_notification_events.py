"""Add notification_events table for delivery audit

Revision ID: f4c1d2e3a4b5
Revises: e1b2c3d4f5a6
Create Date: 2026-02-15 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f4c1d2e3a4b5"
down_revision: Union[str, Sequence[str], None] = "e1b2c3d4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("receiver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("source_session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("receiver_email", sa.String(), nullable=False),
        sa.Column("dedupe_key", sa.String(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_notification_events_channel", "notification_events", ["channel"])
    op.create_index("ix_notification_events_action_type", "notification_events", ["action_type"])
    op.create_index("ix_notification_events_status", "notification_events", ["status"])
    op.create_index("ix_notification_events_receiver_user_id", "notification_events", ["receiver_user_id"])
    op.create_index("ix_notification_events_sender_user_id", "notification_events", ["sender_user_id"])
    op.create_index("ix_notification_events_source_session_id", "notification_events", ["source_session_id"])
    op.create_index("ix_notification_events_receiver_email", "notification_events", ["receiver_email"])
    op.create_index("ix_notification_events_dedupe_key", "notification_events", ["dedupe_key"])
    op.create_index("ix_notification_events_is_read", "notification_events", ["is_read"])
    op.create_index("ix_notification_events_created_at", "notification_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_notification_events_created_at", table_name="notification_events")
    op.drop_index("ix_notification_events_is_read", table_name="notification_events")
    op.drop_index("ix_notification_events_dedupe_key", table_name="notification_events")
    op.drop_index("ix_notification_events_receiver_email", table_name="notification_events")
    op.drop_index("ix_notification_events_source_session_id", table_name="notification_events")
    op.drop_index("ix_notification_events_sender_user_id", table_name="notification_events")
    op.drop_index("ix_notification_events_receiver_user_id", table_name="notification_events")
    op.drop_index("ix_notification_events_status", table_name="notification_events")
    op.drop_index("ix_notification_events_action_type", table_name="notification_events")
    op.drop_index("ix_notification_events_channel", table_name="notification_events")
    op.drop_table("notification_events")
