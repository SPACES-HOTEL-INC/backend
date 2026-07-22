import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat


class PaymentBase(BaseModel):
    booking_id: uuid.UUID
    amount: PositiveFloat
    currency: str | None = Field(default="NGN", max_length=16)
    payment_method: Literal["card", "bank_transfer", "ussd", "paystack", "flutterwave"]


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Literal["pending", "success", "failed", "refunded"] | None = None
    transaction_ref: str | None = Field(None, max_length=255)
    gateway_response: dict | None = None


class PaymentRead(PaymentBase):
    id: uuid.UUID
    status: Literal["pending", "success", "failed", "refunded"]
    transaction_ref: str | None = None
    gateway_response: dict | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
