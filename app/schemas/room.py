import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class RoomBase(BaseModel):
    title: str = Field(max_length=255)
    description: str = Field(max_length=2000)
    price_per_night: float = Field(gt=0)


class RoomCreate(RoomBase):
    images: List[str] = Field(..., min_length=3, max_length=7)


class RoomResponse(RoomBase):
    id: uuid.UUID
    property_id: uuid.UUID
    images: List[str]

    model_config = ConfigDict(from_attributes=True)
