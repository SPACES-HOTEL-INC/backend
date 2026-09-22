from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user
from ..core.security import get_password_hash, verify_password
from ..database import get_async_session
from ..models.property import Property
from ..models.user import User
from ..schemas.settings import (
    BusinessSettingsRead,
    BusinessSettingsUpdate,
    PasswordUpdateRequest,
    PreferencesRead,
    PreferencesUpdate,
    ProfileSettingsRead,
    ProfileSettingsUpdate,
)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

DEFAULT_PREFERENCES: dict[str, Any] = {
    "emailNotifications": True,
    "smsAlerts": False,
    "bookingConfirmations": True,
    "payoutAlerts": True,
    "theme": "dark",
}
USER_PREFERENCES: dict[str, dict[str, Any]] = {}


def _success_response(data: Any | None = None, message: str | None = None):
    payload: dict[str, Any] = {"status": "success"}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    return payload


def _error_response(message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"status": "error", "message": message})


def _serialize_role(role: Any) -> str:
    if role is None:
        return "User"
    value = str(role).strip().lower()
    if value in {"admin", "administrator", "superadmin"}:
        return "Super Admin"
    if value in {"host", "hotel", "manager"}:
        return "Hotel Manager"
    return "User"


def _build_profile_payload(user: User) -> dict[str, Any]:
    return {
        "id": str(user.id),
        "fullName": user.full_name,
        "email": user.email,
        "phone": user.phone_number,
        "avatarUrl": getattr(user, "avatar_url", None),
        "role": _serialize_role(user.role),
    }


def _build_business_payload(user: User, property_obj: Property | None) -> dict[str, Any]:
    business_email = getattr(property_obj, "business_email", None) or user.email
    support_phone = getattr(property_obj, "support_phone", None) or getattr(property_obj, "contact", None) or user.phone_number
    address = getattr(property_obj, "address", None) or "123 Hospitality Way, Abuja, Nigeria"
    return {
        "propertyName": getattr(property_obj, "hotel_name", None) or user.full_name or "Spaces Hotel & Suites",
        "businessEmail": business_email,
        "supportPhone": support_phone,
        "address": address,
        "currency": getattr(property_obj, "currency", None) or "NGN",
        "timezone": getattr(property_obj, "timezone", None) or "Africa/Lagos",
        "logoUrl": getattr(property_obj, "logo_url", None) or getattr(user, "avatar_url", None),
    }


def _get_preferences_for_user(user_id: str) -> dict[str, Any]:
    return USER_PREFERENCES.setdefault(str(user_id), DEFAULT_PREFERENCES.copy())


@router.get("/profile")
async def get_profile_settings(current_user: User = Depends(get_current_user)):
    return _success_response(_build_profile_payload(current_user))


@router.put("/profile")
async def update_profile_settings(
    payload: ProfileSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if payload.fullName is not None:
        current_user.full_name = payload.fullName
    if payload.phone is not None:
        current_user.phone_number = payload.phone
    if payload.avatarUrl is not None:
        setattr(current_user, "avatar_url", payload.avatarUrl)

    session.add(current_user)
    await session.commit()
    await session.refresh(current_user)
    return _success_response(_build_profile_payload(current_user))


@router.get("/business")
async def get_business_settings(current_user: User = Depends(get_current_user)):
    return _success_response(_build_business_payload(current_user, current_user.owned_property))


@router.put("/business")
async def update_business_settings(
    payload: BusinessSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    property_obj = current_user.owned_property
    if property_obj is None:
        property_obj = Property(
            owner_id=current_user.id,
            hotel_name=payload.propertyName or "Spaces Hotel & Suites",
            address=payload.address or "123 Hospitality Way, Abuja, Nigeria",
            contact=payload.supportPhone or current_user.phone_number or current_user.email,
        )
        session.add(property_obj)
    else:
        if payload.propertyName is not None:
            property_obj.hotel_name = payload.propertyName
        if payload.address is not None:
            property_obj.address = payload.address
        if payload.supportPhone is not None:
            property_obj.contact = payload.supportPhone

    if payload.businessEmail is not None:
        setattr(property_obj, "business_email", payload.businessEmail)
    if payload.currency is not None:
        setattr(property_obj, "currency", payload.currency)
    if payload.timezone is not None:
        setattr(property_obj, "timezone", payload.timezone)

    await session.commit()
    await session.refresh(property_obj)
    return _success_response(_build_business_payload(current_user, property_obj))


@router.put("/security/password")
async def update_password_settings(
    payload: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    if not verify_password(payload.currentPassword, current_user.hashed_password):
        return _error_response("Current password does not match.", status_code=400)

    current_user.hashed_password = get_password_hash(payload.newPassword)
    session.add(current_user)
    await session.commit()
    return _success_response(message="Password updated successfully.")


@router.get("/preferences")
async def get_preferences_settings(current_user: User = Depends(get_current_user)):
    preferences = _get_preferences_for_user(str(current_user.id))
    return _success_response({**DEFAULT_PREFERENCES, **preferences})


@router.put("/preferences")
async def update_preferences_settings(
    payload: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
):
    stored_preferences = _get_preferences_for_user(str(current_user.id))
    merged_preferences = {**DEFAULT_PREFERENCES, **stored_preferences, **payload.model_dump(exclude_unset=True)}
    USER_PREFERENCES[str(current_user.id)] = merged_preferences
    return _success_response(merged_preferences)
