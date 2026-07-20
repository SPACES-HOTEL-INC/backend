from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class ReviewBase(BaseModel):
    booking_id: str
    property_id: str
    rating: int
    comment: str | None = None


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: int | None = None
    comment: str | None = None
    host_response: str | None = None


class ReviewRead(ReviewBase):
    id: str
    guest_id: str
    host_response: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
