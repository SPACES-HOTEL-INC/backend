import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class Property(Base):
    __tablename__ = "properties"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    hotel_name = Column(String, nullable=False)
    address = Column(String, nullable=False)
    contact = Column(String, nullable=False)

    description = Column(String, nullable=True)
    property_type = Column(String, nullable=True, default="hotel")
    city = Column(String, nullable=True, index=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True, default="Nigeria")
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    amenities = Column(JSON, nullable=True)
    images = Column(JSON, nullable=True)
    cancellation_policy = Column(String, nullable=True, default="flexible")
    is_verified = Column(Boolean, default=False, nullable=False)
    avg_rating = Column(Float, default=0.0, nullable=False)
    total_reviews = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    balance = Column(Numeric(10, 2), default=0.00)
    bank_details = Column(JSON, nullable=True)

    owner = relationship("User", back_populates="owned_property")
    rooms = relationship("Room", back_populates="property", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="property")

    @property
    def host_id(self):
        return self.owner_id

    @host_id.setter
    def host_id(self, value):
        self.owner_id = value