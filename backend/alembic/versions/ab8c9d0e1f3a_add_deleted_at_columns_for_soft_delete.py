"""Add deleted_at columns for soft-delete lifecycle scaffolding

Revision ID: ab8c9d0e1f3a
Revises: fa7b8c9d0e2
Create Date: 2026-02-17 16:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab8c9d0e1f3a"
down_revision: Union[str, Sequence[str], None] = "fa7b8c9d0e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("journals", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("analyses", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("card_responses", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("card_sessions", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.add_column("notification_events", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)
    op.create_index("ix_journals_deleted_at", "journals", ["deleted_at"], unique=False)
    op.create_index("ix_analyses_deleted_at", "analyses", ["deleted_at"], unique=False)
    op.create_index("ix_card_responses_deleted_at", "card_responses", ["deleted_at"], unique=False)
    op.create_index("ix_card_sessions_deleted_at", "card_sessions", ["deleted_at"], unique=False)
    op.create_index("ix_notification_events_deleted_at", "notification_events", ["deleted_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_events_deleted_at", table_name="notification_events")
    op.drop_index("ix_card_sessions_deleted_at", table_name="card_sessions")
    op.drop_index("ix_card_responses_deleted_at", table_name="card_responses")
    op.drop_index("ix_analyses_deleted_at", table_name="analyses")
    op.drop_index("ix_journals_deleted_at", table_name="journals")
    op.drop_index("ix_users_deleted_at", table_name="users")

    op.drop_column("notification_events", "deleted_at")
    op.drop_column("card_sessions", "deleted_at")
    op.drop_column("card_responses", "deleted_at")
    op.drop_column("analyses", "deleted_at")
    op.drop_column("journals", "deleted_at")
    op.drop_column("users", "deleted_at")
