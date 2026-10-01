"""Payment model: money collected against a booking."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PaymentMethod(str, enum.Enum):
    """Supported payment rails. Added here means a migration to widen the enum."""
    card = "card"
    bank_transfer = "bank_transfer"
    ussd = "ussd"
    paystack = "paystack"
    flutterwave = "flutterwave"


class PaymentStatus(str, enum.Enum):
    pending = "pending"
    success = "success"
    failed = "failed"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False)
    # Money, so Numeric (exact) rather than Float (rounding).
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(16), nullable=False, default="NGN")
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    # The gateway's own reference, used to match webhooks back to this row.
    # Unique so a gateway event cannot be applied twice.
    transaction_ref = Column(String(255), unique=True, nullable=True)
    # Raw provider response, kept for debugging disputes.
    gateway_response = Column(JSONB, nullable=True)
    # Set once the status becomes success; null while unpaid.
    paid_at = Column(DateTime(timezone=True), nullable=True)
    # NOTE: utcnow returns a naive UTC datetime, unlike the other models which
    # use a timezone-aware default. Pre-existing inconsistency, left as-is so
    # existing rows are not reinterpreted.
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    booking = relationship("Booking", back_populates="payment")
