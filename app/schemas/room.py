import uuid
from typing import List

from pydantic import BaseModel, ConfigDict, Field, computed_field


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

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @computed_field
    @property
    def name(self) -> str:
        return self.title

    @computed_field
    @property
    def price(self) -> float:
        return self.price_per_night

    @computed_field
    @property
    def currency(self) -> str:
        return "₦"

    @computed_field
    @property
    def capacity(self) -> int:
        return 2

    @computed_field
    @property
    def inventory(self) -> int:
        return 1

    @computed_field
    @property
    def is_available(self) -> bool:
        return True

    @computed_field
    @property
    def status(self) -> str:
        return "active"
