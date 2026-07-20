import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.booking import Booking, BookingStatus
from ..models.room import Room
from ..schemas.booking import BookingCreate, BookingUpdate


async def create_booking(session: AsyncSession, booking: BookingCreate, user_id: uuid.UUID) -> Booking:
    result = await session.execute(select(Room).where(Room.id == booking.room_id))
    room = result.scalar_one_or_none()

    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="The requested room does not exist.")

    db_booking = Booking(
        user_id=user_id,
        room_id=booking.room_id,
        status=BookingStatus.PENDING,
    )
    if booking.check_in is not None:
        db_booking.check_in = booking.check_in
    if booking.check_out is not None:
        db_booking.check_out = booking.check_out
    if booking.total_price is not None:
        db_booking.total_price = booking.total_price
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking


async def get_booking_by_id(session: AsyncSession, booking_id: uuid.UUID) -> Optional[Booking]:
    result = await session.execute(select(Booking).where(Booking.id == booking_id))
    return result.scalar_one_or_none()


async def get_user_bookings(session: AsyncSession, user_id: uuid.UUID) -> List[Booking]:
    result = await session.execute(select(Booking).where(Booking.user_id == user_id))
    return list(result.scalars().all())


async def get_pending_bookings_for_hotel(session: AsyncSession, property_id: uuid.UUID) -> List[Booking]:
    result = await session.execute(
        select(Booking)
        .join(Room, Booking.room_id == Room.id)
        .where(Room.property_id == property_id)
        .where(Booking.status == BookingStatus.PENDING)
    )
    return list(result.scalars().all())


async def update_booking(session: AsyncSession, booking_id: uuid.UUID, booking_update: BookingUpdate) -> Booking:
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
    db_booking = await get_booking_by_id(session, booking_id)
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db_booking.status = BookingStatus.CANCELLED
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking


async def get_conflicting_bookings(session: AsyncSession, room_id: uuid.UUID, check_in: datetime, check_out: datetime) -> List[Booking]:
    result = await session.execute(
        select(Booking).where(
            Booking.room_id == room_id,
            Booking.status != BookingStatus.CANCELLED,
        )
    )
    return list(result.scalars().all())


async def list_bookings_for_guest(session: AsyncSession, user_id: uuid.UUID) -> List[Booking]:
    result = await session.execute(select(Booking).where(Booking.user_id == user_id))
    return list(result.scalars().all())


async def list_bookings_for_host(session: AsyncSession, property_id: uuid.UUID) -> List[Booking]:
    result = await session.execute(
        select(Booking).join(Room, Booking.room_id == Room.id).where(Room.property_id == property_id)
    )
    return list(result.scalars().all())


async def update_booking_status(session: AsyncSession, booking_id: uuid.UUID, status: str) -> Booking:
    db_booking = await get_booking_by_id(session, booking_id)
    if not db_booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    db_booking.status = BookingStatus(status)
    session.add(db_booking)
    await session.commit()
    await session.refresh(db_booking)
    return db_booking