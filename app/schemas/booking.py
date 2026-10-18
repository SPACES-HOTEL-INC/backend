"""Request and response schemas for bookings."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookingBase(BaseModel):
    """Fields a client sends when requesting a booking."""

    room_id: uuid.UUID
    # Accepted for convenience but the room alone determines the property.
    property_id: uuid.UUID | None = None
    # The API takes dates, not timestamps; the model stores timestamps.
    check_in_date: date | None = None
    check_out_date: date | None = None
    num_guests: int = 1
    special_requests: str | None = Field(None, max_length=2000)
    # Optional: when omitted, the price is worked out from the room's nightly
    # rate, so the client cannot underpay by sending a low number.
    total_price: float | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, values):
        """Accept the older check_in/check_out/guest_id field names."""
        if isinstance(values, dict):
            if values.get("check_in_date") is None and values.get("check_in") is not None:
                values["check_in_date"] = values["check_in"]
            if values.get("check_out_date") is None and values.get("check_out") is not None:
                values["check_out_date"] = values["check_out"]
            if values.get("guest_id") is not None and values.get("user_id") is None:
                values["user_id"] = values["guest_id"]
        return values

    @model_validator(mode="after")
    def validate_dates(self):
        """A stay must end after it starts. Anything else is a 422.

        Overlap with an existing booking and past dates are checked in the CRUD
        layer, since those need a database query.
        """
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValueError("check_out_date must be after check_in_date")
        return self

    @property
    def check_in(self) -> date | None:
        """Alias the CRUD layer uses when reading a booking."""
        return self.check_in_date

    @property
    def check_out(self) -> date | None:
        return self.check_out_date


class BookingCreate(BookingBase):
    """Create payload. Everything is inherited from BookingBase."""


class BookingUpdate(BaseModel):
    """Partial update: a status change and/or edited special requests."""

    # Mirrors BookingStatus. Kept as a Literal so the API documents the values
    # without importing the model layer.
    status: Literal["pending", "confirmed", "cancelled", "completed", "no_show"] | None = None
    special_requests: str | None = Field(None, max_length=2000)


class BookingRead(BookingBase):
    """A booking as returned to clients."""

    id: uuid.UUID
    # Read from the model's `guest_id` property, which mirrors user_id.
    guest_id: uuid.UUID
    num_nights: int | None = None
    total_price: float | None = None
    status: Literal["pending", "confirmed", "cancelled", "completed", "no_show"]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingReadWithRelations(BookingRead):
    """BookingRead plus denormalised guest and property names.

    Used by the host bookings list so the dashboard does not have to make a
    second request per row to label them.
    """

    guest_name: str | None = None
    guest_email: str | None = None
    room_title: str | None = None
    property_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
