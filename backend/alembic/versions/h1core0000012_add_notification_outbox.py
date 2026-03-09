"""Add durable notification outbox table.

Revision ID: h1core0000012
Revises: h1core0000011
Create Date: 2026-03-01
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000012"
down_revision: Union[str, Sequence[str], None] = "h1core0000011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("receiver_email", sa.String(length=320), nullable=False),
        sa.Column("sender_name", sa.String(length=255), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=True),
        sa.Column("receiver_user_id", sa.Uuid(), nullable=True),
        sa.Column("sender_user_id", sa.Uuid(), nullable=True),
        sa.Column("source_session_id", sa.Uuid(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("dedupe_slot_reserved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default=sa.text("3")),
        sa.Column("available_at", sa.DateTime(), nullable=False),
        sa.Column("last_attempt_at", sa.DateTime(), nullable=True),
        sa.Column("last_error_reason", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["receiver_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_outbox_status", "notification_outbox", ["status"])
    op.create_index("ix_notification_outbox_available_at", "notification_outbox", ["available_at"])
    op.create_index(
        "ix_notification_outbox_status_available_at",
        "notification_outbox",
        ["status", "available_at"],
    )
    op.create_index("ix_notification_outbox_receiver_email", "notification_outbox", ["receiver_email"])
    op.create_index("ix_notification_outbox_action_type", "notification_outbox", ["action_type"])
    op.create_index("ix_notification_outbox_event_type", "notification_outbox", ["event_type"])
    op.create_index("ix_notification_outbox_receiver_user_id", "notification_outbox", ["receiver_user_id"])
    op.create_index("ix_notification_outbox_sender_user_id", "notification_outbox", ["sender_user_id"])
    op.create_index("ix_notification_outbox_source_session_id", "notification_outbox", ["source_session_id"])
    op.create_index("ix_notification_outbox_dedupe_key", "notification_outbox", ["dedupe_key"])


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_dedupe_key", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_source_session_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_sender_user_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_receiver_user_id", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_event_type", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_action_type", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_receiver_email", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_status_available_at", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_available_at", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_table("notification_outbox")
