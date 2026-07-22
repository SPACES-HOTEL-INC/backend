import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr = Field(max_length=255)
    role: str = "consumer"


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)


class UserResponse(UserBase):
    id: uuid.UUID
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = Field(None, max_length=255)
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role: Optional[str] = Field(None, max_length=32)
    full_name: Optional[str] = Field(None, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=32)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: str
    is_active: bool = True
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
