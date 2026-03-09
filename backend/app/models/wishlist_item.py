# Module D2: Shared blueprint / wishlist (couple).

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utcnow


class WishlistItem(SQLModel, table=True):
    __tablename__ = "wishlist_items"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # who added
    partner_id: uuid.UUID = Field(foreign_key="users.id", index=True)  # pair
    title: str = Field(max_length=500)
    notes: str = Field(max_length=2000, default="")
    created_at: datetime = Field(default_factory=utcnow)
