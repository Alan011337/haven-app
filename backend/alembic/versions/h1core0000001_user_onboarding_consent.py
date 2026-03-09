"""Add user_onboarding_consent table (Module A1).

Revision ID: h1core0000001
Revises: g1p2b0000003
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000001"
down_revision: Union[str, Sequence[str], None] = "g1p2b0000003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_onboarding_consent",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("privacy_scope_accepted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notification_frequency", sa.String(length=32), nullable=False, server_default="normal"),
        sa.Column("ai_intensity", sa.String(length=32), nullable=False, server_default="gentle"),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_onboarding_consent")
