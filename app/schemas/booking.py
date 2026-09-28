import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BookingBase(BaseModel):
    room_id: uuid.UUID
    property_id: uuid.UUID | None = None
    check_in_date: date | None = None
    check_out_date: date | None = None
    num_guests: int = 1
    special_requests: str | None = Field(None, max_length=2000)
    total_price: float | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_fields(cls, values):
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
        if self.check_in_date and self.check_out_date:
            if self.check_out_date <= self.check_in_date:
                raise ValueError("check_out_date must be after check_in_date")
        return self

    @property
    def check_in(self) -> date | None:
        return self.check_in_date

    @property
    def check_out(self) -> date | None:
        return self.check_out_date


class BookingCreate(BookingBase):
    pass


class BookingUpdate(BaseModel):
    status: Literal["pending", "confirmed", "cancelled", "completed", "no_show"] | None = None
    special_requests: str | None = Field(None, max_length=2000)


class BookingRead(BookingBase):
    id: uuid.UUID
    guest_id: uuid.UUID
    num_nights: int | None = None
    total_price: float | None = None
    status: Literal["pending", "confirmed", "cancelled", "completed", "no_show"]
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class BookingReadWithRelations(BookingRead):
    guest_name: str | None = None
    guest_email: str | None = None
    room_title: str | None = None
    property_name: str | None = None

    model_config = ConfigDict(from_attributes=True)
