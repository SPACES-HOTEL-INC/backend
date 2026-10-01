"""Property model: a hotel or short-stay rental owned by one user."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    # The account that owns and manages this property. Ownership checks compare
    # this against the logged-in user's id.
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    hotel_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    # Free-form contact string built from the email/phone submitted at creation.
    contact = Column(String, nullable=False)

    description = Column(String, nullable=True)
    property_type = Column(String, nullable=True, default="hotel")
    # Indexed so property search can filter by city.
    city = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, default="Nigeria")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    # Both JSON arrays of strings; Cloudinary or local image URLs.
    amenities = Column(JSON, nullable=True)
    images = Column(JSON, nullable=True)
    cancellation_policy = Column(String, nullable=True, default="flexible")
    # Set by an admin once the listing has been reviewed.
    is_verified = Column(Boolean, default=False, nullable=False)
    # Denormalised review figures, kept in sync so listings do not need an
    # aggregate query on every read.
    avg_rating = Column(Float, default=0.0, nullable=False)
    total_reviews = Column(Integer, default=0, nullable=False)
    # Python-side callables so both timestamps come from the application clock.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    # Soft delete: listings are deactivated rather than removed so booking
    # history keeps its reference. Indexed to keep searches fast.
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Money, so Numeric rather than Float. Scale 2, two decimal places.
    balance = Column(Numeric(10, 2), default=0.00)
    bank_details = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="owned_property")
    # delete-orphan: removing a property takes its rooms with it.
    rooms = relationship("Room", back_populates="property", cascade="all, delete-orphan")
    # No cascade: reviews outlive a property so history is never lost.
    reviews = relationship("Review", back_populates="property")

    @property
    def host_id(self):
        """Alias of `owner_id`, kept for older call sites."""
        return self.owner_id

    @host_id.setter
    def host_id(self, value):
        self.owner_id = value