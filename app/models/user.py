import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM as PGEnum, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class UserRole(str, PyEnum):
    CONSUMER = "consumer"
    HOST = "host"
    ADMIN = "admin"

    @classmethod
    def coerce(cls, value):
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.CONSUMER
        if isinstance(value, str):
            normalized = value.strip().lower()
            mapping = {
                "hotel": cls.HOST, "host": cls.HOST, "hot": cls.HOST,
                "admin": cls.ADMIN, "administrator": cls.ADMIN, "superadmin": cls.ADMIN,
                "consumer": cls.CONSUMER, "guest": cls.CONSUMER, "user": cls.CONSUMER, "customer": cls.CONSUMER,
            }
            if normalized in mapping:
                return mapping[normalized]
        return cls(value)


class UserRoleType(TypeDecorator):
    impl = String
    cache_ok = True

    _ROLE_MAPPING = {
        UserRole.CONSUMER: "CONSUMER",
        UserRole.HOST: "HOTEL",
        UserRole.ADMIN: "ADMIN",
    }

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return PGEnum(
                "CONSUMER", "HOTEL", "ADMIN",
                name="userrole",
                create_type=False,
            )
        return String()

    def process_bind_param(self, value, dialect):
        if value is None:
            return "CONSUMER"
        if isinstance(value, UserRole):
            return self._ROLE_MAPPING.get(value, "CONSUMER")
        return str(value).upper()

    def process_result_value(self, value, dialect):
        if value is None:
            return UserRole.CONSUMER
        normalized = str(value).strip().lower()
        mapping = {
            "consumer": UserRole.CONSUMER, "guest": UserRole.CONSUMER, "user": UserRole.CONSUMER,
            "hotel": UserRole.HOST, "host": UserRole.HOST, "hot": UserRole.HOST,
            "admin": UserRole.ADMIN, "administrator": UserRole.ADMIN, "superadmin": UserRole.ADMIN,
        }
        return mapping.get(normalized, UserRole.CONSUMER)

    def bind_processor(self, dialect):
        return lambda value: self.process_bind_param(value, dialect)


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    _role = Column("role", UserRoleType, nullable=False, default="CONSUMER")

    owned_property = relationship("Property", back_populates="owner", uselist=False)
    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="guest")

    is_active = Column(Boolean, default=True, nullable=False)

    @property
    def role(self) -> UserRole:
        value = self._role
        if value is None:
            return UserRole.CONSUMER
        if isinstance(value, UserRole):
            return value
        normalized = str(value).strip().upper()
        if normalized == "HOTEL":
            return UserRole.HOST
        if normalized == "ADMIN":
            return UserRole.ADMIN
        return UserRole.CONSUMER

    @role.setter
    def role(self, value: UserRole | str | None):
        if value is None:
            self._role = "CONSUMER"
        elif isinstance(value, UserRole):
            if value == UserRole.HOST:
                self._role = "HOTEL"
            elif value == UserRole.ADMIN:
                self._role = "ADMIN"
            else:
                self._role = "CONSUMER"
        else:
            coerced = UserRole.coerce(value)
            if coerced == UserRole.HOST:
                self._role = "HOTEL"
            elif coerced == UserRole.ADMIN:
                self._role = "ADMIN"
            else:
                self._role = "CONSUMER"

    def has_role(self, role: UserRole | str) -> bool:
        if isinstance(role, str):
            role = UserRole(role)
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
