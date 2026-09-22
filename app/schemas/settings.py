from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProfileSettingsRead(BaseModel):
    id: str
    fullName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatarUrl: Optional[str] = None
    role: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ProfileSettingsUpdate(BaseModel):
    fullName: Optional[str] = Field(default=None, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=32)
    avatarUrl: Optional[str] = Field(default=None, max_length=500)


class BusinessSettingsRead(BaseModel):
    propertyName: Optional[str] = None
    businessEmail: Optional[str] = None
    supportPhone: Optional[str] = None
    address: Optional[str] = None
    currency: str = "NGN"
    timezone: str = "Africa/Lagos"
    logoUrl: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class BusinessSettingsUpdate(BaseModel):
    propertyName: Optional[str] = Field(default=None, max_length=255)
    businessEmail: Optional[str] = Field(default=None, max_length=255)
    supportPhone: Optional[str] = Field(default=None, max_length=32)
    address: Optional[str] = Field(default=None, max_length=500)
    currency: Optional[str] = Field(default=None, max_length=16)
    timezone: Optional[str] = Field(default=None, max_length=64)


class PasswordUpdateRequest(BaseModel):
    currentPassword: str = Field(..., min_length=8, max_length=128)
    newPassword: str = Field(..., min_length=8, max_length=128)
    confirmPassword: str = Field(..., min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_password_confirmation(self):
        if self.newPassword != self.confirmPassword:
            raise ValueError("New password and confirm password must match.")
        return self


class PreferencesRead(BaseModel):
    emailNotifications: bool = True
    smsAlerts: bool = False
    bookingConfirmations: bool = True
    payoutAlerts: bool = True
    theme: str = "dark"

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PreferencesUpdate(PreferencesRead):
    pass
