import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReviewBase(BaseModel):
    booking_id: uuid.UUID
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class ReviewCreate(ReviewBase):
    pass


class ReviewUpdate(BaseModel):
    rating: int | None = Field(None, ge=1, le=5)
    comment: str | None = Field(None, max_length=2000)


class HostResponseUpdate(BaseModel):
    host_response: str = Field(max_length=2000)


class ReviewRead(ReviewBase):
    id: uuid.UUID
    guest_id: uuid.UUID
    host_response: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
