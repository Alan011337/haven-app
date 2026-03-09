"""Add consent_receipts table and user birth_year/terms_accepted_at columns

Revision ID: b2c3d4e5f6a7
Revises: ab8c9d0e1f3a
Create Date: 2026-02-20 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "ab8c9d0e1f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = :n"
        ),
        {"n": name},
    ).scalar()
    return r is not None


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar()
    return r is not None


def upgrade() -> None:
    conn = op.get_bind()

    # --- consent_receipts table (skip if already exists) ---
    if not _table_exists(conn, "consent_receipts"):
        op.create_table(
            "consent_receipts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("consent_type", sa.String(length=64), nullable=False),
            sa.Column("policy_version", sa.String(length=32), nullable=False),
            sa.Column("granted_at", sa.DateTime(), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("ip_address", sa.String(length=45), nullable=True),
        )
        op.create_index("ix_consent_receipts_user_id", "consent_receipts", ["user_id"])
        op.create_index("ix_consent_receipts_consent_type", "consent_receipts", ["consent_type"])
        op.create_index("ix_consent_receipts_user_type", "consent_receipts", ["user_id", "consent_type"])

    # --- user age & terms fields (skip if already exist) ---
    if not _column_exists(conn, "users", "birth_year"):
        op.add_column("users", sa.Column("birth_year", sa.Integer(), nullable=True))
    if not _column_exists(conn, "users", "terms_accepted_at"):
        op.add_column("users", sa.Column("terms_accepted_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "terms_accepted_at")
    op.drop_column("users", "birth_year")

    op.drop_index("ix_consent_receipts_user_type", table_name="consent_receipts")
    op.drop_index("ix_consent_receipts_consent_type", table_name="consent_receipts")
    op.drop_index("ix_consent_receipts_user_id", table_name="consent_receipts")
    op.drop_table("consent_receipts")
