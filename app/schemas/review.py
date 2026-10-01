"""Request and response schemas for reviews."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    """Fields a client sends when leaving a review."""

    booking_id: uuid.UUID
    # ge=1, le=5 keeps ratings inside the five-star scale.
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    """Create payload. Guest and property are derived from the booking."""


class ReviewUpdate(BaseModel):
    """Partial update. The rating, if changed, needs to be folded back into the
    property's cached average by the CRUD layer."""

    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class HostResponseUpdate(BaseModel):
    """The property owner's public reply to a review."""

    host_response: str = Field(max_length=2000)


class ReviewRead(ReviewBase):
    """A review as returned to clients, including the host's reply."""

    id: uuid.UUID
    guest_id: uuid.UUID
    # Null until the host has replied.
    host_response: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
