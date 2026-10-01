"""Request and response schemas for properties.

The validators exist to absorb inconsistent input from the frontend rather
than to reject it: they lowercase enum-ish strings and map older field names
onto their current equivalents.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PropertyBase(BaseModel):
    """Fields a client may send when creating a property."""

    # `name` is accepted as an alias for hotel_name; see normalize_legacy_fields.
    hotel_name: str | None = None
    description: str | None = None
    # Literal, so an unexpected value is a 422 rather than bad data.
    property_type: Literal["hotel", "apartment", "resort", "short_stay"] = "hotel"
    address: str
    city: str | None = None
    state: str | None = None
    country: str | None = "Nigeria"
    latitude: float | None = None
    longitude: float | None = None
    amenities: list[str] | None = None
    images: list[str] | None = None
    contact: str | None = None
    cancellation_policy: Literal["flexible", "moderate", "strict"] = "flexible"
    is_active: bool | None = True

    @field_validator("property_type", mode="before")
    @classmethod
    def normalize_property_type(cls, v: str | None) -> str | None:
        """Accept "Hotel" as well as "hotel"."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("cancellation_policy", mode="before")
    @classmethod
    def normalize_cancellation_policy(cls, v: str | None) -> str | None:
        """Accept "Flexible" as well as "flexible"."""
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, values):
        """Backfill older payload shapes so older clients keep working.

        `name` becomes `hotel_name`, and a missing `address` falls back to
        `city` (address is required, city was the only field sent before).
        """
        if isinstance(values, dict):
            if values.get("hotel_name") is None and values.get("name"):
                values["hotel_name"] = values["name"]
            if values.get("address") is None and values.get("city"):
                values["address"] = values["city"]
        return values


class PropertyCreate(PropertyBase):
    """Create payload. Everything is inherited from PropertyBase."""


class PropertyUpdate(BaseModel):
    """Partial update. Every field is optional; only what is sent is applied.

    `host_id`, ratings and timestamps are absent on purpose: ownership and
    review figures are never client-settable.
    """

    hotel_name: str | None = None
    description: str | None = None
    property_type: Literal["hotel", "apartment", "resort", "short_stay"] | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    amenities: list[str] | None = None
    images: list[str] | None = None
    contact: str | None = None
    cancellation_policy: Literal["flexible", "moderate", "strict"] | None = None
    is_active: bool | None = None

    @field_validator("property_type", "cancellation_policy", mode="before")
    @classmethod
    def normalize_enums(cls, v: str | None) -> str | None:
        """Apply the same lowercasing as PropertyBase on updates."""
        if isinstance(v, str):
            return v.strip().lower()
        return v


class PropertyRead(PropertyBase):
    """A property as returned to clients, including server-managed fields."""

    id: uuid.UUID
    # The owner's user id. Read from the model's `host_id` property.
    host_id: uuid.UUID
    is_verified: bool = False
    avg_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)