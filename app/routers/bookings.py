import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_host
from ..crud.booking import (
    create_booking, 
    get_booking_by_id, 
    list_bookings_for_guest, 
    list_bookings_for_host, 
    cancel_booking
)
from ..crud.property import get_property_by_id
from ..database import get_async_session
from ..schemas.booking import BookingCreate, BookingRead
from ..models.user import User

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking_endpoint(
    booking_in: BookingCreate, 
    user = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    return await create_booking(session, booking_in, user.id)


@router.get("/mine", response_model=list[BookingRead])
async def get_my_bookings(
    user = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    return await list_bookings_for_guest(session, user.id)


@router.get("/host-bookings", response_model=list[BookingRead])
async def get_my_property_bookings(
    user = Depends(require_host), 
    session: AsyncSession = Depends(get_async_session)
):
    return await list_bookings_for_host(session, user.id)


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: uuid.UUID, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.user_id) != str(user.id) and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return booking


@router.delete("/{booking_id}", response_model=BookingRead)
async def cancel_booking_endpoint(
    booking_id: uuid.UUID, 
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.user_id) != str(user.id) and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await cancel_booking(session, booking_id)
