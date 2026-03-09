"""Add auth_refresh_sessions table

Revision ID: f1a2b3c4d5e6
Revises: f0a1b2c3d4e5
Create Date: 2026-02-23 10:55:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "f0a1b2c3d4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("current_token_hash", sa.String(length=128), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("client_ip_hash", sa.String(length=128), nullable=True),
        sa.Column("user_agent_hash", sa.String(length=128), nullable=True),
        sa.Column("rotation_counter", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_rotated_at", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replayed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_auth_refresh_sessions_user_id", "auth_refresh_sessions", ["user_id"], unique=False)
    op.create_index(
        "ix_auth_refresh_sessions_current_token_hash",
        "auth_refresh_sessions",
        ["current_token_hash"],
        unique=False,
    )
    op.create_index("ix_auth_refresh_sessions_device_id", "auth_refresh_sessions", ["device_id"], unique=False)
    op.create_index("ix_auth_refresh_sessions_created_at", "auth_refresh_sessions", ["created_at"], unique=False)
    op.create_index("ix_auth_refresh_sessions_expires_at", "auth_refresh_sessions", ["expires_at"], unique=False)
    op.create_index("ix_auth_refresh_sessions_revoked_at", "auth_refresh_sessions", ["revoked_at"], unique=False)
    op.create_index("ix_auth_refresh_sessions_replayed_at", "auth_refresh_sessions", ["replayed_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_sessions_replayed_at", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_revoked_at", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_expires_at", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_created_at", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_device_id", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_current_token_hash", table_name="auth_refresh_sessions")
    op.drop_index("ix_auth_refresh_sessions_user_id", table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
