import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.dependencies import get_current_user
from ..crud.booking import get_booking_by_id
from ..crud.payment import create_payment, get_payment_by_id, list_payments_for_guest, update_payment
from ..database import get_async_session
from ..models.payment import Payment
from ..schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])


@router.post("/initiate", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def initiate_payment(payment_in: PaymentCreate, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    booking = await get_booking_by_id(session, payment_in.booking_id)
    if not booking or str(booking.user_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not authorized")
    return await create_payment(session, payment_in)


@router.get("/mine", response_model=list[PaymentRead])
async def read_my_payments(user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    return await list_payments_for_guest(session, str(user.id))


@router.get("/{payment_id}", response_model=PaymentRead)
async def read_payment(payment_id: uuid.UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    result = await session.execute(
        select(Payment).options(selectinload(Payment.booking)).where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    if str(payment.booking.user_id) != str(user.id) and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return payment


@router.post("/webhook")
async def payment_webhook(
    payload: dict,
    x_webhook_secret: str | None = Header(None, alias="X-Webhook-Secret"),
):
    webhook_secret = os.getenv("PAYMENT_WEBHOOK_SECRET")
    if not webhook_secret:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Webhook secret not configured")
    if not x_webhook_secret or x_webhook_secret != webhook_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook secret")
    return {"detail": "Webhook endpoint not implemented."}
