"""Room model: one bookable unit within a property."""

import uuid
from sqlalchemy import Column, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # Deleting a property removes its rooms at the database level as well.
    property_id = Column(UUID(as_uuid=True), ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    # Indexed for "cheapest available" style queries.
    price_per_night = Column(Float, nullable=False, index=True)

    # Store dynamic image lists directly as JSON string arrays
    images = Column(JSON, nullable=False)

    # Relationships
    property = relationship("Property", back_populates="rooms")
    # Bookings are removed with the room, matching the CASCADE above.
    bookings = relationship("Booking", back_populates="room", cascade="all, delete-orphan")