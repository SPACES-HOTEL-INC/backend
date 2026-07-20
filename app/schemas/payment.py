from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class PaymentBase(BaseModel):
    booking_id: str
    amount: float
    currency: str | None = "NGN"
    payment_method: Literal["card", "bank_transfer", "ussd", "paystack", "flutterwave"]


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    status: Literal["pending", "success", "failed", "refunded"] | None = None
    transaction_ref: str | None = None
    gateway_response: dict | None = None


class PaymentRead(PaymentBase):
    id: str
    status: Literal["pending", "success", "failed", "refunded"]
    transaction_ref: str | None = None
    gateway_response: dict | None = None
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
