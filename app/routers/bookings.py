"""Booking endpoints for guests and hosts.

Pricing, availability and status rules all live in the CRUD layer; these
handlers deal only with identity and authorization. `/mine` and
`/host-bookings` are declared before `/{booking_id}` so the literals win the
route match.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_hotel_staff, require_host
from ..crud.booking import (
    create_booking,
    get_booking_by_id,
    list_bookings_for_guest,
    list_bookings_for_hotel,
    list_bookings_for_host,
    cancel_booking,
    release_booking_wallet_funds,
)
from ..crud.property import get_property_by_id
from ..database import get_async_session
from ..models.booking import BookingStatus
from ..models.user import User
from ..schemas.booking import BookingCheckIn, BookingCreate, BookingRead, BookingReadWithRelations

router = APIRouter(prefix="/api/v1/bookings", tags=["bookings"])


@router.post("/", response_model=BookingRead, status_code=status.HTTP_201_CREATED)
async def create_booking_endpoint(
    booking_in: BookingCreate,
    user = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Book a room as the signed-in guest.

    The guest id comes from the token, never the request body, so a user cannot
    book on someone else's behalf.
    """
    return await create_booking(session, booking_in, user.id)


@router.get("/mine", response_model=list[BookingRead])
async def get_my_bookings(
    user = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Bookings the signed-in guest made, across all their properties."""
    return await list_bookings_for_guest(session, user.id)


@router.get("/host-bookings", response_model=list[BookingReadWithRelations])
async def get_my_property_bookings(
    user = Depends(require_hotel_staff),
    session: AsyncSession = Depends(get_async_session)
):
    """Bookings received across the hotel's properties, with guest and property
    details included. Receptionists see the same hotel-wide booking feed without
    owning the property themselves."""
    if user.is_receptionist:
        return await list_bookings_for_hotel(session, user.hotel_id)
    return await list_bookings_for_host(session, user.id)


@router.get("/{booking_id}", response_model=BookingRead)
async def get_booking(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Fetch one booking. Only the guest who made it, or an admin, may read it.

    Note the host cannot read it here; hosts go through `/host-bookings`.
    """
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.user_id) != str(user.id) and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return booking


@router.post("/{booking_id}/check-in", response_model=BookingRead)
async def check_in_booking_endpoint(
    booking_id: uuid.UUID,
    payload: BookingCheckIn,
    user: User = Depends(require_hotel_staff),
    session: AsyncSession = Depends(get_async_session)
):
    """Validate the guest's SPC code and mark them as checked in.

    Only hotel staff can do this; the guest can no longer cancel once the code has
    been used to start the stay.
    """
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.status == BookingStatus.CANCELLED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is cancelled and cannot be checked in.")
    if booking.status == BookingStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking already completed.")
    if booking.spc_code is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This booking has no SPC code assigned.")

    if booking.spc_code.strip().upper() != payload.spc_code.strip().upper():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid SPC code.")

    booking.status = BookingStatus.CHECKED_IN
    booking.checked_in_at = datetime.now(timezone.utc)
    await release_booking_wallet_funds(session, booking_id)
    session.add(booking)
    await session.commit()
    await session.refresh(booking)
    return booking


@router.delete("/{booking_id}", response_model=BookingRead)
async def cancel_booking_endpoint(
    booking_id: uuid.UUID,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session)
):
    """Cancel a booking. Same ownership rule as reading one.

    Whether the cancellation is allowed for the current status, and what happens
    to any payment, is decided in the CRUD layer.
    """
    booking = await get_booking_by_id(session, booking_id)
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if str(booking.user_id) != str(user.id) and not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return await cancel_booking(session, booking_id)
