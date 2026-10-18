"""Booking model: a guest's reservation of one room for a date range."""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class BookingStatus(str, PyEnum):
    """Lifecycle of a reservation.

    New bookings start PENDING; a host or the system moves them to CONFIRMED,
    then COMPLETED, or CANCELLED / NO_SHOW if the stay does not happen.
    """

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The room reserved, and the guest who reserved it.
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(
        # native_enum=False stores this as VARCHAR + a CHECK constraint rather
        # than a Postgres enum, so adding a status does not need a type migration.
        SQLEnum(BookingStatus, native_enum=False),
        nullable=False,
        default=BookingStatus.PENDING,
    )
    # Stored as timestamps, though the API accepts and returns dates.
    # Overlap queries treat them as a half-open range: [check_in, check_out).
    check_in = Column(DateTime(timezone=True), nullable=True)
    check_out = Column(DateTime(timezone=True), nullable=True)
    # Priced at creation time so later rate changes do not alter past bookings.
    total_price = Column(Float, nullable=True)
    # Database-side default as well, so rows created outside the app still get one.
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    room = relationship("Room", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    # One-to-one: a booking has at most one payment attempt and one review.
    payment = relationship("Payment", back_populates="booking")
    review = relationship("Review", back_populates="booking")

    @property
    def guest_id(self):
        """Alias of `user_id`, kept for older call sites."""
        return self.user_id

    @guest_id.setter
    def guest_id(self, value):
        self.user_id = value