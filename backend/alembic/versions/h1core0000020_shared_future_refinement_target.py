"""Add target_wishlist_item_id to relationship_knowledge_suggestions.

Revision ID: h1core0000020
Revises: h1core0000019
Create Date: 2026-04-01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "h1core0000020"
down_revision: Union[str, Sequence[str], None] = "h1core0000019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "relationship_knowledge_suggestions",
        sa.Column(
            "target_wishlist_item_id",
            sa.Uuid(),
            sa.ForeignKey("wishlist_items.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_relationship_knowledge_suggestions_target_wishlist_item_id",
        "relationship_knowledge_suggestions",
        ["target_wishlist_item_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_relationship_knowledge_suggestions_target_wishlist_item_id",
        table_name="relationship_knowledge_suggestions",
    )
    op.drop_column("relationship_knowledge_suggestions", "target_wishlist_item_id")
