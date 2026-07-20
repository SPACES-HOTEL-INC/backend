from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user
from ..crud.payment import create_payment, get_payment_by_id, list_payments_for_guest, list_payments_for_booking, update_payment
from ..crud.booking import get_booking_by_id
from ..database import get_async_session
from ..schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentRead)
async def initiate_payment(payment_in: PaymentCreate, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    booking = await get_booking_by_id(session, payment_in.booking_id)
    if not booking or str(booking.guest_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not authorized")
    return await create_payment(session, payment_in)


@router.get("/mine", response_model=list[PaymentRead])
async def read_my_payments(user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return await list_payments_for_guest(session, str(user.id))


@router.get("/{payment_id}", response_model=PaymentRead)
async def read_payment(payment_id: str, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    payment = await get_payment_by_id(session, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if str(payment.booking.guest_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return payment


@router.post("/webhook")
async def payment_webhook(payload: dict):
    return {"detail": "Webhook endpoint not implemented."}
