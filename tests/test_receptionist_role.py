import asyncio
import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.models.user import User, UserRole
from app.routers.auth import register
from app.schemas.user import UserCreate


def test_receptionist_role_is_recognized():
    assert UserRole.coerce("receptionist") == UserRole.RECEPTIONIST
    assert UserRole.coerce("reception") == UserRole.RECEPTIONIST


def test_user_can_hold_receptionist_role():
    user = User(email="staff@example.com", hashed_password="hash")
    user.role = UserRole.RECEPTIONIST
    assert user.role == UserRole.RECEPTIONIST
    assert user.has_role(UserRole.RECEPTIONIST)
    assert user.is_host is False
    assert user.is_admin is False


def test_receptionist_self_registration_is_rejected():
    async def _run():
        with patch("app.routers.auth.get_user_by_email", new=AsyncMock(return_value=None)):
            with pytest.raises(HTTPException) as exc:
                await register(
                    UserCreate(email="staff@example.com", password="StrongPass123", role="receptionist"),
                    session=AsyncMock(),
                )
        assert exc.value.status_code == 403
        assert "hotel" in str(exc.value.detail).lower()

    asyncio.run(_run())


def test_receptionist_is_bound_to_the_creating_hotel():
    host = User(email="host@example.com", hashed_password="hash")
    host.id = uuid.uuid4()
    host.role = UserRole.HOST

    other_hotel = User(email="other@example.com", hashed_password="hash")
    other_hotel.id = uuid.uuid4()

    receptionist = User(email="staff@example.com", hashed_password="hash")
    receptionist.role = UserRole.RECEPTIONIST
    receptionist.hotel_id = host.id

    assert receptionist.can_access_hotel(host.id)
    assert not receptionist.can_access_hotel(other_hotel.id)
