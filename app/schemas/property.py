import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator


class PropertyBase(BaseModel):
    hotel_name: str | None = None
    description: str | None = None
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
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @field_validator("cancellation_policy", mode="before")
    @classmethod
    def normalize_cancellation_policy(cls, v: str | None) -> str | None:
        if isinstance(v, str):
            return v.strip().lower()
        return v

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, values):
        if isinstance(values, dict):
            if values.get("hotel_name") is None and values.get("name"):
                values["hotel_name"] = values["name"]
            if values.get("address") is None and values.get("city"):
                values["address"] = values["city"]
        return values


class PropertyCreate(PropertyBase):
    pass


class PropertyUpdate(BaseModel):
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
        if isinstance(v, str):
            return v.strip().lower()
        return v


class PropertyRead(PropertyBase):
    id: uuid.UUID
    host_id: uuid.UUID
    is_verified: bool = False
    avg_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)