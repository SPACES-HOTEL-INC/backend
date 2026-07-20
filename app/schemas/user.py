import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr

from ..models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.CONSUMER


class UserCreate(UserBase):
    password: str
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class UserResponse(UserBase):
    id: int
    full_name: Optional[str] = None
    phone_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)