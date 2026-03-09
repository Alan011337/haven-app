"""Add entitlement_usage_daily table

Revision ID: f2b3c4d5e6f7
Revises: f1a2b3c4d5e6
Create Date: 2026-02-23 12:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "entitlement_usage_daily",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("feature_key", sa.String(length=128), nullable=False),
        sa.Column("usage_date", sa.Date(), nullable=False),
        sa.Column("used_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entitlement_usage_daily_created_at", "entitlement_usage_daily", ["created_at"], unique=False)
    op.create_index("ix_entitlement_usage_daily_feature_key", "entitlement_usage_daily", ["feature_key"], unique=False)
    op.create_index("ix_entitlement_usage_daily_updated_at", "entitlement_usage_daily", ["updated_at"], unique=False)
    op.create_index("ix_entitlement_usage_daily_usage_date", "entitlement_usage_daily", ["usage_date"], unique=False)
    op.create_index("ix_entitlement_usage_daily_user_id", "entitlement_usage_daily", ["user_id"], unique=False)
    op.create_index(
        "ix_entitlement_usage_daily_user_date",
        "entitlement_usage_daily",
        ["user_id", "usage_date"],
        unique=False,
    )
    op.create_index(
        "uq_entitlement_usage_daily_user_feature_date",
        "entitlement_usage_daily",
        ["user_id", "feature_key", "usage_date"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_entitlement_usage_daily_user_feature_date", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_user_date", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_user_id", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_usage_date", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_updated_at", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_feature_key", table_name="entitlement_usage_daily")
    op.drop_index("ix_entitlement_usage_daily_created_at", table_name="entitlement_usage_daily")
    op.drop_table("entitlement_usage_daily")
