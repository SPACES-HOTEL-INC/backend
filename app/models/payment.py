import enum
import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class PaymentMethod(str, enum.Enum):
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
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(16), nullable=False, default="NGN")
    payment_method = Column(Enum(PaymentMethod), nullable=False)
    status = Column(Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending)
    transaction_ref = Column(String(255), unique=True, nullable=True)
    gateway_response = Column(JSONB, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    booking = relationship("Booking", back_populates="payment")
