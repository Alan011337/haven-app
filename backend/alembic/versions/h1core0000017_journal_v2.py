"""Add Journal V2 visibility and attachment support.

Revision ID: h1core0000017
Revises: h1core0000016
Create Date: 2026-03-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000017"
down_revision: Union[str, Sequence[str], None] = "h1core0000016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "journals",
        sa.Column(
            "visibility",
            sa.String(length=32),
            nullable=False,
            server_default="PARTNER_TRANSLATED_ONLY",
        ),
    )
    op.add_column(
        "journals",
        sa.Column(
            "content_format",
            sa.String(length=32),
            nullable=False,
            server_default="markdown",
        ),
    )
    op.add_column(
        "journals",
        sa.Column(
            "partner_translation_status",
            sa.String(length=32),
            nullable=False,
            server_default="NOT_REQUESTED",
        ),
    )
    op.add_column(
        "journals",
        sa.Column("partner_translated_content", sa.Text(), nullable=True),
    )
    op.create_index("ix_journals_visibility", "journals", ["visibility"], unique=False)

    op.create_table(
        "journal_attachments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("journal_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(length=512), nullable=False),
        sa.Column("caption", sa.String(length=280), nullable=True),
        sa.ForeignKeyConstraint(["journal_id"], ["journals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_journal_attachments_deleted_at",
        "journal_attachments",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_journal_attachments_journal_deleted_created",
        "journal_attachments",
        ["journal_id", "deleted_at", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_journal_attachments_journal_deleted_created",
        table_name="journal_attachments",
    )
    op.drop_index("ix_journal_attachments_deleted_at", table_name="journal_attachments")
    op.drop_table("journal_attachments")

    op.drop_index("ix_journals_visibility", table_name="journals")
    op.drop_column("journals", "partner_translated_content")
    op.drop_column("journals", "partner_translation_status")
    op.drop_column("journals", "content_format")
    op.drop_column("journals", "visibility")
