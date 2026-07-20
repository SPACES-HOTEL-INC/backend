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
from ..database import get_async_session
from ..schemas.booking import BookingCreate # Import your Booking schema here

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])

@router.post("/")
async def create_booking_endpoint(
    booking_in: BookingCreate, 
    user = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    return await create_booking(session, booking_in, user.id)

@router.get("/mine")
async def get_my_bookings(
    user = Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    return await list_bookings_for_guest(session, user.id)

@router.get("/host-bookings")
async def get_my_property_bookings(
    user = Depends(require_host), 
    session: AsyncSession = Depends(get_async_session)
):
    return await list_bookings_for_host(session, user.id)

@router.get("/{booking_id}")
async def get_booking(
    booking_id: str, 
    session: AsyncSession = Depends(get_async_session)
):
    booking = await get_booking_by_id(session, uuid.UUID(booking_id))
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking

@router.delete("/{booking_id}")
async def cancel_booking_endpoint(
    booking_id: str, 
    session: AsyncSession = Depends(get_async_session)
):
    return await cancel_booking(session, uuid.UUID(booking_id))