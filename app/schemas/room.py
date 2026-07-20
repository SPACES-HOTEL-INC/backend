from typing import List

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class RoomBase(BaseModel):
    title: str
    description: str
    price_per_night: float


class RoomCreate(RoomBase):
    images: List[HttpUrl] = Field(..., min_length=3, max_length=7)


class RoomResponse(RoomBase):
    id: str
    property_id: str
    images: List[str]

    model_config = ConfigDict(from_attributes=True)