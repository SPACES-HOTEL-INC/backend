"""Database operations for bookings.

This module raises `HTTPException` directly rather than ValueError, unlike
crud/user.py, because every failure here maps to a specific status code the
router should pass straight through.
"""

import uuid
from datetime import date, datetime
from enum import Enum as PyEnum
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Add the Property model to your model imports here:
from ..models.property import Property
from ..models.booking import Booking, BookingStatus
from ..models.room import Room
from ..schemas.booking import BookingCreate, BookingUpdate
from ..models.user import User


async def create_booking(session: AsyncSession, booking: BookingCreate, user_id: uuid.UUID) -> Booking:
    """Validate and insert a new booking for `user_id`.

    Checks, in order: both dates present, check-out after check-in, check-in not
    in the past, the room exists, and the dates are free.
    """
    # Accept either the current field name or the legacy alias.
    check_in = booking.check_in_date or booking.check_in
    check_out = booking.check_out_date or booking.check_out

    if check_in is None or check_out is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both check_in_date and check_out_date are required.",
        )
    if check_out <= check_in:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="check_out_date must be after check_in_date.",
        )
    if check_in < date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="check_in_date cannot be in the past.",
        )

    result = await session.execute(select(Room).where(Room.id == booking.room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested room does not exist.")

    # Reject the booking if the room is already taken for any overlapping night.
    conflicts = await get_conflicting_bookings(session, booking.room_id, check_in, check_out)
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This room is already booked for the selected dates.",
        )

    # Price server-side when the client did not supply one, so a guest cannot
    # book a stay at an arbitrary amount.
    total_price = booking.total_price
    if total_price is None:
        num_nights = (check_out - check_in).days
        total_price = room.price_per_night * num_nights

    db_booking = Booking(
        user_id=user_id,
        room_id=booking.room_id,
        # Every new booking starts unconfirmed.
        status=BookingStatus.PENDING,
        check_in=check_in,
        check_out=check_out,
        total_price=total_price,
    )
    db_booking.room = room
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking


async def get_booking_by_id(session: AsyncSession, booking_id: uuid.UUID) -> Optional[Booking]:
    """Fetch one booking, or None. Callers do the ownership check."""
    result = await session.execute(select(Booking).options(selectinload(Booking.room)).where(Booking.id == booking_id))
    return result.scalar_one_or_none()


async def get_user_bookings(session: AsyncSession, user_id: uuid.UUID) -> List[Booking]:
    """Every booking made by this user, in any status."""
    result = await session.execute(select(Booking).options(selectinload(Booking.room)).where(Booking.user_id == user_id))
    return list(result.scalars().all())


async def get_pending_bookings_for_hotel(session: AsyncSession, property_id: uuid.UUID) -> List[Booking]:
    """Bookings awaiting confirmation across every room in one property.

    Joins through Room because a booking references a room, not a property.
    """
    result = await session.execute(
        select(Booking)
        .join(Room, Booking.room_id == Room.id)
        .where(Room.property_id == property_id)
        .where(Booking.status == BookingStatus.PENDING)
    )
    return list(result.scalars().all())


async def update_booking(session: AsyncSession, booking_id: uuid.UUID, booking_update: BookingUpdate) -> Booking:
    """Apply a partial update, restricted to an allowlist of fields.

    The allowlist stops a caller from writing id, user_id or room_id through an
    update payload.
    """
    db_booking = await get_booking_by_id(session, booking_id)
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    update_data = booking_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key in {"check_in", "check_out", "total_price", "status"}:
            setattr(db_booking, key, value)

    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking


async def cancel_booking(session: AsyncSession, booking_id: uuid.UUID) -> Booking:
    """Mark a booking cancelled.

    The row is kept rather than deleted, so payment and review history survive.
    """
    db_booking = await get_booking_by_id(session, booking_id)
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db_booking.status = BookingStatus.CANCELLED
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking


async def get_conflicting_bookings(
    session: AsyncSession, room_id: uuid.UUID, check_in: date, check_out: date
) -> List[Booking]:
    """Bookings for this room whose dates overlap [check_in, check_out).

    The overlap test treats stays as half-open ranges, so a guest checking out
    on the same day another checks in is not a conflict. Cancelled bookings are
    ignored because they free the room up.
    """
    result = await session.execute(
        select(Booking).where(
            Booking.room_id == room_id,
            Booking.status != BookingStatus.CANCELLED,
            # existing starts before this stay ends
            Booking.check_in < check_out,
            # and existing ends after this stay starts
            Booking.check_out > check_in,
        )
    )
    return list(result.scalars().all())


async def list_bookings_for_guest(session: AsyncSession, user_id: uuid.UUID) -> List[Booking]:
    """Bookings this user made as a guest, for the "my bookings" screen."""
    result = await session.execute(select(Booking).options(selectinload(Booking.room)).where(Booking.user_id == user_id))
    return list(result.scalars().all())


async def list_bookings_for_host(session: AsyncSession, host_id: uuid.UUID) -> List[Booking]:
    """Bookings against any property this host owns.

    Walks Booking -> Room -> Property to reach the owner. The selectinload calls
    eager-load the guest and room/property rows so the dashboard can label each
    booking without an extra query per row.
    """
    result = await session.execute(
        select(Booking)
        .join(Room, Booking.room_id == Room.id)
        .join(Property, Room.property_id == Property.id)
        .where(Property.owner_id == host_id)
        .options(
            selectinload(Booking.room).selectinload(Room.property),
            selectinload(Booking.user),
        )
    )
    return list(result.scalars().all())


async def update_booking_status(session: AsyncSession, booking_id: uuid.UUID, status: str) -> Booking:
    """Move a booking to a new status, validating the value.

    NOTE: currently unused; the router uses the update endpoint instead.
    """
    db_booking = await get_booking_by_id(session, booking_id)
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db_booking.status = BookingStatus(status)
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking
