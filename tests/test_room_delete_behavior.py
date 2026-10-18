import asyncio
from unittest.mock import AsyncMock

from app.crud.room import room_has_active_bookings


from unittest.mock import AsyncMock, MagicMock


def test_room_has_active_bookings_returns_true_for_active_booking():
    async def _run():
        session = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = object()
        session.execute = AsyncMock(return_value=result)

        return await room_has_active_bookings(session, "room-123")

    assert asyncio.run(_run()) is True


def test_room_has_active_bookings_returns_false_when_only_cancelled_or_completed():
    async def _run():
        session = AsyncMock()
        result = MagicMock()
        result.scalar.return_value = None
        session.execute = AsyncMock(return_value=result)

        return await room_has_active_bookings(session, "room-456")

    assert asyncio.run(_run()) is False
