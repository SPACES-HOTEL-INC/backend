import uuid
from datetime import date, datetime
from enum import Enum as PyEnum

from sqlalchemy import Column, Date, DateTime, Enum as SQLEnum, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from ..database import Base


class BookingStatus(str, PyEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    room_id = Column(UUID(as_uuid=True), ForeignKey("rooms.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status = Column(SQLEnum(BookingStatus, native_enum=False), nullable=False, default=BookingStatus.PENDING)
    check_in = Column(Date, nullable=True)
    check_out = Column(Date, nullable=True)
    total_price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    room = relationship("Room", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    payment = relationship("Payment", back_populates="booking")
    review = relationship("Review", back_populates="booking")

    @property
    def guest_id(self):
        return self.user_id

    @guest_id.setter
    def guest_id(self, value):
        self.user_id = value