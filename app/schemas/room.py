"""Request and response schemas for rooms."""

import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field, computed_field


class RoomBase(BaseModel):
    """Fields a client sends when creating or editing a room."""

    title: str = Field(max_length=255)
    description: str = Field(max_length=2000)
    # gt=0 rejects zero and negative nightly rates.
    price_per_night: float = Field(gt=0)


class RoomCreate(RoomBase):
    """Create payload.

    A room needs between 3 and 7 photos for the listing gallery.
    """

    images: List[str] = Field(..., min_length=3, max_length=7)


class RoomResponse(RoomBase):
    """A room as returned to clients.

    The `computed_field` properties below are presentation-only aliases and
    hard-coded values the frontend expects. They are derived, not stored:
    capacity, inventory, availability and status are placeholders until rooms
    gain real occupancy and availability data.
    """

    id: uuid.UUID
    property_id: uuid.UUID
    images: List[str]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def name(self) -> str:
        """Alias of `title`."""
        return self.title

    @computed_field
    @property
    def price(self) -> float:
        """Alias of `price_per_night`."""
        return self.price_per_night

    @computed_field
    @property
    def currency(self) -> str:
        # Hard-coded naira symbol. Every price in the system is currently NGN.
        return "₦"

    @computed_field
    @property
    def capacity(self) -> int:
        """Placeholder: rooms have no stored occupancy limit yet."""
        return 2

    @computed_field
    @property
    def inventory(self) -> int:
        """Placeholder: availability is not yet calculated from bookings."""
        return 1

    @computed_field
    @property
    def is_available(self) -> bool:
        """Placeholder: always true. Date-range availability is not implemented."""
        return True

    @computed_field
    @property
    def status(self) -> str:
        """Placeholder: rooms have no status column."""
        return "active"
