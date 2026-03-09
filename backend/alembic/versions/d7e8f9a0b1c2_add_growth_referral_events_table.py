"""Add growth_referral_events table

Revision ID: d7e8f9a0b1c2
Revises: c3d4e5f6a7b8
Create Date: 2026-02-22 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "growth_referral_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("invite_code_hash", sa.String(length=64), nullable=False),
        sa.Column("dedupe_key", sa.String(length=64), nullable=False),
        sa.Column("metadata_json", sa.String(length=1024), nullable=True),
        sa.Column("inviter_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["inviter_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_growth_referral_events_created_at",
        "growth_referral_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_updated_at",
        "growth_referral_events",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_event_type",
        "growth_referral_events",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_source",
        "growth_referral_events",
        ["source"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_invite_code_hash",
        "growth_referral_events",
        ["invite_code_hash"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_inviter_user_id",
        "growth_referral_events",
        ["inviter_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_actor_user_id",
        "growth_referral_events",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index(
        "uq_growth_referral_events_dedupe_key",
        "growth_referral_events",
        ["dedupe_key"],
        unique=True,
    )
    op.create_index(
        "ix_growth_referral_events_type_created_at",
        "growth_referral_events",
        ["event_type", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_inviter_created_at",
        "growth_referral_events",
        ["inviter_user_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_growth_referral_events_actor_created_at",
        "growth_referral_events",
        ["actor_user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_growth_referral_events_actor_created_at", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_inviter_created_at", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_type_created_at", table_name="growth_referral_events")
    op.drop_index("uq_growth_referral_events_dedupe_key", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_actor_user_id", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_inviter_user_id", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_invite_code_hash", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_source", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_event_type", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_updated_at", table_name="growth_referral_events")
    op.drop_index("ix_growth_referral_events_created_at", table_name="growth_referral_events")
    op.drop_table("growth_referral_events")
