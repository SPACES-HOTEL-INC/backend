"""User model and the role system.

An account has a primary `role` (stored in the Postgres `userrole` enum) and a
`roles` list holding every role it holds, so one person can be a hotel owner and
a consumer on the same account.
"""

import uuid
from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, JSON, String, TypeDecorator
from sqlalchemy.dialects.postgresql import ENUM as PGEnum, UUID
from sqlalchemy.orm import relationship

from ..database import Base


class UserRole(str, PyEnum):
    """The three roles in the system.

    Inherits from `str` so members compare and serialise like plain strings.
    """

    CONSUMER = "consumer"
    HOST = "host"
    ADMIN = "admin"

    @classmethod
    def coerce(cls, value):
        """Map any known spelling of a role onto a `UserRole`.

        The API, the frontend and the database all use different words for the
        same role ("hotel", "host", "manager"), so normalise at the boundary and
        fall back to CONSUMER rather than raising on unfamiliar input.
        """
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
    """Stores a `UserRole` in the Postgres `userrole` enum.

    Python speaks "host" while the database stores "HOTEL", so both directions
    translate here and the rest of the codebase never sees the mismatch.
    """

    impl = String
    # Lets SQLAlchemy cache compiled statements for this type.
    cache_ok = True

    _ROLE_MAPPING = {
        UserRole.CONSUMER: "CONSUMER",
        UserRole.HOST: "HOTEL",
        UserRole.ADMIN: "ADMIN",
    }

    def load_dialect_impl(self, dialect):
        """Use the real enum on Postgres, plain VARCHAR elsewhere (e.g. tests)."""
        if dialect.name == "postgresql":
            return PGEnum(
                "CONSUMER", "HOTEL", "ADMIN",
                name="userrole",
                # The type is created by a migration, not by table creation.
                create_type=False,
            )
        return String()

    def process_bind_param(self, value, dialect):
        """Python value -> database value."""
        if value is None:
            return "CONSUMER"
        if isinstance(value, UserRole):
            return self._ROLE_MAPPING.get(value, "CONSUMER")
        return str(value).upper()

    def process_result_value(self, value, dialect):
        """Database value -> `UserRole`."""
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
    """A person with an account.

    `email` is unique: one row per address, always. Holding more than one role
    is expressed through `roles`, never by creating a second row.
    """

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Unique and indexed because every login and OTP lookup goes through it.
    email = Column(String, unique=True, index=True, nullable=False)
    # bcrypt hash. The plaintext password is never stored.
    hashed_password = Column(String, nullable=False)

    full_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    # Named `_role` because `role` is the property below; the column is called
    # "role" in the database.
    _role = Column("role", UserRoleType, nullable=False, default="CONSUMER")

    # Every role this account holds. `role` above stays the primary role so all
    # existing reads, gates and enum storage keep behaving exactly as before.
    roles = Column(JSON, nullable=False, default=list)

    # A user manages at most one property in the current design.
    owned_property = relationship("Property", back_populates="owner", uselist=False)
    bookings = relationship("Booking", back_populates="user")
    reviews = relationship("Review", back_populates="guest")

    # Setting this to False blocks login without deleting the account or its data.
    is_active = Column(Boolean, default=True, nullable=False)

    # Email OTP verification state. Login is refused until is_verified is True.
    is_verified = Column(Boolean, default=False, nullable=False)
    # Stores an HMAC-SHA256 hex digest of the OTP, not the 6-digit code itself.
    # Both are cleared once the code is accepted.
    otp_code = Column(String(64), nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def role(self) -> UserRole:
        """The primary role as a `UserRole`.

        Setter and getter both translate between the database's "HOTEL" and the
        enum's "host", so callers can use `user.role` freely.
        """
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

    def get_roles(self) -> set[UserRole]:
        """Every role this account holds, primary role included.

        Rows created before the `roles` column existed have an empty list, so
        the primary role is merged in as the floor. This keeps pre-migration
        accounts behaving exactly as they did.
        """
        resolved = {self.role}
        for raw in self.roles or []:
            try:
                resolved.add(UserRole.coerce(raw))
            except ValueError:
                continue
        return resolved

    def add_role(self, role: UserRole | str | None) -> bool:
        """Grant an additional role, leaving the primary role untouched.

        Returns True when the role was newly granted.
        """
        resolved = UserRole.coerce(role)
        current = self.get_roles()
        if resolved in current:
            return False
        current.add(resolved)
        # CONSUMER first, then HOST, then ADMIN, so the list reads predictably.
        order = [UserRole.CONSUMER, UserRole.HOST, UserRole.ADMIN]
        self.roles = [r.value for r in order if r in current]
        return True

    def has_role(self, role: UserRole | str) -> bool:
        """True when the account holds this role, by any spelling of it.

        An unrecognised value returns False rather than raising, so a bad entry
        in `roles` can never lock a user out of their own account.
        """
        try:
            resolved = role if isinstance(role, UserRole) else UserRole.coerce(role)
        except ValueError:
            return False
        return resolved in self.get_roles()

    @property
    def is_host(self) -> bool:
        """True for hotel owners and for admins, who can do everything a host can."""
        return self.has_role(UserRole.HOST) or self.has_role(UserRole.ADMIN)

    @property
    def is_admin(self) -> bool:
        """True only for admins. Gates the destructive admin routes."""
        return self.has_role(UserRole.ADMIN)

    @property
    def is_hotel(self) -> bool:
        """Alias of `is_host`, kept for older call sites."""
        return self.is_host
