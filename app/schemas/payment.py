"""Request and response schemas for payments.

Status and method are Literals so the allowed values appear in the API docs and
an unexpected value is rejected with a 422.
"""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveFloat


class PaymentBase(BaseModel):
    booking_id: uuid.UUID
    # PositiveFloat rejects zero and negative charges.
    amount: PositiveFloat
    currency: str | None = Field(default="NGN", max_length=16)
    payment_method: Literal["card", "bank_transfer", "ussd", "paystack", "flutterwave"]


class PaymentCreate(PaymentBase):
    """Payment initiation payload."""


class PaymentUpdate(BaseModel):
    """Partial update, used when a gateway callback confirms or voids a payment.

    NOTE: nothing calls this yet. Payment status is currently only ever set to
    "pending" at creation.
    """

    status: Literal["pending", "success", "failed", "refunded"] | None = None
    transaction_ref: str | None = Field(None, max_length=255)
    # Raw provider payload, stored for dispute debugging.
    gateway_response: dict | None = None


class PaymentRead(PaymentBase):
    """A payment as returned to clients."""

    id: uuid.UUID
    status: Literal["pending", "success", "failed", "refunded"]
    transaction_ref: str | None = None
    gateway_response: dict | None = None
    # Null until the payment succeeds.
    paid_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
