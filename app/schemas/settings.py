"""Schemas for the account settings screens.

These use camelCase field names (`fullName`, not `full_name`) to match what the
frontend sends and expects, so unlike the other schema modules the naming here
is deliberately not snake_case.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileSettingsRead(BaseModel):
    """The signed-in user's own profile."""

    id: str
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    # A display label such as "Hotel Manager", not the raw role value.
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProfileSettingsUpdate(BaseModel):
    """Profile edits. Email is absent on purpose: changing it needs re-verification."""

    fullName: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)


class BusinessSettingsRead(BaseModel):
    """Hotel-level settings, sourced from the user's property."""

    propertyName: Optional[str] = None
    businessEmail: Optional[str] = None
    supportPhone: Optional[str] = None
    address: Optional[str] = None
    currency: str = "NGN"
    timezone: str = "Africa/Lagos"
    logoUrl: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BusinessSettingsUpdate(BaseModel):
    """Partial business update. Only fields that are sent get written."""

    propertyName: Optional[str] = Field(default=None, max_length=255)
    businessEmail: Optional[str] = Field(default=None, max_length=255)
    supportPhone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = Field(default=None, max_length=500)
    currency: Optional[str] = Field(default=None, max_length=16)
    timezone: Optional[str] = Field(default=None, max_length=64)


class PasswordUpdateRequest(BaseModel):
    """Password change. The current password is re-checked in the router."""

    currentPassword: str = Field(..., min_length=8, max_length=128)
    newPassword: str = Field(..., min_length=8, max_length=128)
    confirmPassword: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        """Catch a typo before the router does any hashing or database work."""
        if self.newPassword != self.confirmPassword:
            raise ValueError("New password and confirm password must match.")
        return self


class PreferencesRead(BaseModel):
    """Notification and display preferences.

    NOTE: these are held in an in-memory dict in the router, so they reset when
    the process restarts. They are not persisted yet.
    """

    emailNotifications: bool = True
    smsAlerts: bool = False
    bookingConfirmations: bool = True
    payoutAlerts: bool = True
    theme: str = "dark"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PreferencesUpdate(PreferencesRead):
    """Partial preferences update; inherited fields are all optional-by-default."""

