"""Request and response schemas for users and authentication.

Read schemas set `from_attributes=True` so FastAPI can serialise an ORM model
directly. Request schemas carry the validation rules, so invalid input is
rejected with a 422 before any handler runs.
"""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


class UserBase(BaseModel):
    """Fields common to every user payload."""

    # EmailStr validates the address is well formed, not just a string.
    email: EmailStr = Field(max_length=255)
    # Free string, not an enum, because the frontend sends several spellings.
    # UserRole.coerce() normalises it; unknown values fall back to consumer.
    role: str = "consumer"


class UserCreate(UserBase):
    """Signup payload. The account starts unverified; OTP decides when it opens."""

    # Minimum 8 characters enforced here, hashed before it is stored.
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)


class UserResponse(UserBase):
    """Minimal user representation for embedding in other responses."""

    id: uuid.UUID
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Partial update. Every field is optional; only what is sent is applied."""

    email: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    # Changing a role is admin-only and is stripped from the payload otherwise.
    role: Optional[str] = Field(None, max_length=32)
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)


class Token(BaseModel):
    """Returned by login and refresh. The client sends `access_token` as a bearer."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    """Login payload. No minimum length here, so a wrong password returns 401
    rather than 422 and does not reveal the password policy."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    """The account shape returned by the user and auth routes."""

    id: uuid.UUID
    email: EmailStr
    # Primary role, unchanged for existing clients.
    role: str
    is_active: bool = True
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    is_verified: bool = False
    # Every role held. Rows predating the roles column fall back to the primary
    # role so those accounts still report something meaningful.
    roles: list[str] = Field(default_factory=list)

    @field_validator("roles", mode="before")
    @classmethod
    def null_roles_to_empty(cls, value):
        """Treat a null column as an empty list so the field never fails validation."""
        return [] if value is None else value

    @model_validator(mode="after")
    def backfill_roles(self) -> "UserRead":
        """Always report at least the primary role."""
        if not self.roles:
            self.roles = [self.role]
        return self

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """`token` is the single-purpose reset JWT from the forgot-password email."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class OTPVerifyRequest(BaseModel):
    """Submit the emailed code. The pattern rejects non-numeric codes with 422."""

    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class OTPResendRequest(BaseModel):
    email: EmailStr


class OTPMessage(BaseModel):
    """Response from the OTP routes. Deliberately never includes the code."""

    message: str
    email: EmailStr
    is_verified: bool = False


class RegisterResponse(UserRead):
    """Extends UserRead with the OTP dispatch notice, keeping every existing field."""

    message: str = "Account created. A 6-digit verification code has been sent to your email."
