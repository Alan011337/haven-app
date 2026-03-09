"""P2-I [ADMIN-02]: Content moderation — content_reports table

Revision ID: g1p2i0000001
Revises: g1p2f0000001
Create Date: 2026-02-26

- content_reports: user reports on content (Whisper Wall, Deck Marketplace, etc.)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "g1p2i0000001"
down_revision: Union[str, Sequence[str], None] = "g1p2f0000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=False),
        sa.Column("reporter_user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewer_admin_id", sa.Uuid(), nullable=True),
        sa.Column("resolution_note", sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["reviewer_admin_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_content_reports_status_created_at",
        "content_reports",
        ["status", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_content_reports_resource",
        "content_reports",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index("ix_content_reports_created_at", "content_reports", ["created_at"], unique=False)
    op.create_index("ix_content_reports_reporter_user_id", "content_reports", ["reporter_user_id"], unique=False)
    op.create_index("ix_content_reports_resource_id", "content_reports", ["resource_id"], unique=False)
    op.create_index("ix_content_reports_resource_type", "content_reports", ["resource_type"], unique=False)
    op.create_index("ix_content_reports_status", "content_reports", ["status"], unique=False)
    op.create_index("ix_content_reports_reviewer_admin_id", "content_reports", ["reviewer_admin_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_content_reports_reviewer_admin_id", table_name="content_reports")
    op.drop_index("ix_content_reports_status", table_name="content_reports")
    op.drop_index("ix_content_reports_resource_type", table_name="content_reports")
    op.drop_index("ix_content_reports_resource_id", table_name="content_reports")
    op.drop_index("ix_content_reports_reporter_user_id", table_name="content_reports")
    op.drop_index("ix_content_reports_created_at", table_name="content_reports")
    op.drop_index("ix_content_reports_resource", table_name="content_reports")
    op.drop_index("ix_content_reports_status_created_at", table_name="content_reports")
    op.drop_table("content_reports")
