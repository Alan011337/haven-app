"""Add API idempotency records and events daily rollup tables.

Revision ID: h1core0000016
Revises: h1core0000015
Create Date: 2026-03-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000016"
down_revision: Union[str, Sequence[str], None] = "h1core0000015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "api_idempotency_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("scope_fingerprint", sa.String(length=128), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("route_path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_payload_json", sa.String(length=65535), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_api_idempotency_scope_key",
        "api_idempotency_records",
        ["scope_fingerprint", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_api_idempotency_expires_at",
        "api_idempotency_records",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_created_at",
        "api_idempotency_records",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_updated_at",
        "api_idempotency_records",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_scope_fingerprint",
        "api_idempotency_records",
        ["scope_fingerprint"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_idempotency_key",
        "api_idempotency_records",
        ["idempotency_key"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_method",
        "api_idempotency_records",
        ["method"],
        unique=False,
    )
    op.create_index(
        "ix_api_idempotency_records_route_path",
        "api_idempotency_records",
        ["route_path"],
        unique=False,
    )

    op.create_table(
        "events_log_daily_rollups",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("rollup_date", sa.Date(), nullable=False),
        sa.Column("event_name", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("user_scope", sa.String(length=32), nullable=False),
        sa.Column("event_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_events_rollup_daily_event_source_scope",
        "events_log_daily_rollups",
        ["rollup_date", "event_name", "source", "user_scope"],
        unique=True,
    )
    op.create_index(
        "ix_events_rollup_daily_date",
        "events_log_daily_rollups",
        ["rollup_date"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_created_at",
        "events_log_daily_rollups",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_updated_at",
        "events_log_daily_rollups",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_rollup_date",
        "events_log_daily_rollups",
        ["rollup_date"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_event_name",
        "events_log_daily_rollups",
        ["event_name"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_source",
        "events_log_daily_rollups",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_events_log_daily_rollups_user_scope",
        "events_log_daily_rollups",
        ["user_scope"],
        unique=False,
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_user_scope")
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_source")
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_event_name")
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_rollup_date")
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_events_log_daily_rollups_created_at")
    op.execute("DROP INDEX IF EXISTS ix_events_rollup_daily_date")
    op.execute("DROP INDEX IF EXISTS uq_events_rollup_daily_event_source_scope")
    op.execute("DROP TABLE IF EXISTS events_log_daily_rollups")

    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_route_path")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_method")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_idempotency_key")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_scope_fingerprint")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_updated_at")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_records_created_at")
    op.execute("DROP INDEX IF EXISTS ix_api_idempotency_expires_at")
    op.execute("DROP INDEX IF EXISTS uq_api_idempotency_scope_key")
    op.execute("DROP TABLE IF EXISTS api_idempotency_records")
