"""Review model: a guest's rating of a stay, optionally answered by the host."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Review(Base):
    __tablename__ = "reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Unique: one review per booking, so a guest cannot review a stay twice.
    booking_id = Column(UUID(as_uuid=True), ForeignKey("bookings.id"), nullable=False, unique=True)
    # Denormalised from the booking so reviews can be listed by guest or
    # property without joining through bookings.
    guest_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id"), nullable=False)
    # 1-5. The API layer is responsible for rejecting values outside that range.
    rating = Column(Integer, nullable=False)
    # Text, not String: comments are long-form and unbounded.
    comment = Column(Text, nullable=True)
    # The property owner's public reply. Null until the host responds.
    host_response = Column(Text, nullable=True)
    # Naive UTC, matching Payment rather than Property/Booking.
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    booking = relationship("Booking", back_populates="review")
    guest = relationship("User", back_populates="reviews")
    property = relationship("Property", back_populates="reviews")
