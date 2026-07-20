import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import TypeDecorator

from ..database import Base


class UserRole(str, PyEnum):
    CONSUMER = "consumer"
    HOST = "host"
    ADMIN = "admin"
    HOTEL = "HOTEL"

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.CONSUMER
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"hotel", "host", "hot"}:
                return cls.HOST
            if normalized in {"admin", "administrator", "superadmin"}:
                return cls.ADMIN
            if normalized in {"consumer", "guest", "user", "customer"}:
                return cls.CONSUMER
            if normalized in {"hotel", "host"}:
                return cls.HOST
            if normalized in {"consumer", "guest", "user", "customer"}:
                return cls.CONSUMER
            if normalized in {"admin", "administrator", "superadmin"}:
                return cls.ADMIN
            if normalized in {"hotel", "host"}:
                return cls.HOST
            if normalized in {"consumer", "guest", "user", "customer"}:
                return cls.CONSUMER
        return cls(value)


class UserRoleType(TypeDecorator):
    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        role = UserRole.coerce(value)
        if role == UserRole.HOST:
            return "HOTEL"
        if role == UserRole.ADMIN:
            return "ADMIN"
        return "CONSUMER"

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, UserRole):
            return value
        normalized = str(value).strip().upper()
        if normalized in {"HOTEL", "HOST"}:
            return UserRole.HOST
        if normalized in {"ADMIN"}:
            return UserRole.ADMIN
        return UserRole.CONSUMER


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    role = Column(UserRoleType, nullable=False, default=UserRole.CONSUMER)

    owned_property = relationship("Property", back_populates="owner", uselist=False)
    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="guest")

    is_active = Column(Boolean, default=True, nullable=False)

    def has_role(self, role: UserRole | str) -> bool:
        if isinstance(role, str):
            role = UserRole.coerce(role)
        return self.role == role

    @property
    def is_host(self) -> bool:
        return self.has_role(UserRole.HOST) or self.has_role(UserRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        return self.has_role(UserRole.ADMIN)

    @property
    def is_hotel(self) -> bool:
        return self.is_host

