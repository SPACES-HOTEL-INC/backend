"""Payment endpoints.

The app creates a gateway payment reference on initiation and verifies the
callback signature before updating the local payment record.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import settings
from ..core.dependencies import get_current_user
from ..core.flutterwave import (
    build_checkout_payload,
    create_flutterwave_payment,
    make_tx_ref,
    verify_flutterwave_transaction,
    verify_webhook_signature,
)
from ..crud.booking import (
    get_booking_by_id,
    hold_booking_wallet_funds,
    reverse_booking_wallet_hold,
)
from ..crud.payment import (
    create_payment,
    get_payment_by_id,
    get_payment_by_transaction_ref,
    list_payments_for_guest,
    update_payment,
)
from ..database import get_async_session
from ..models.payment import Payment, PaymentStatus
from ..schemas.payment import PaymentCreate, PaymentRead, PaymentUpdate

router = APIRouter(prefix="/api/v1/payments", tags=["payments"])
callback_router = APIRouter(tags=["payments"])


@router.post("/initiate", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
async def initiate_payment(
    payment_in: PaymentCreate,
    request: Request,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Start a payment against one of the caller's own bookings."""
    booking = await get_booking_by_id(session, payment_in.booking_id)
    if not booking or str(booking.user_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not authorized")

    if booking.total_price is not None:
        booking_total = float(booking.total_price)
        request_total = float(payment_in.amount)
        if abs(request_total - booking_total) > 0.01:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payment amount does not match the booking total")

    payment = await create_payment(session, payment_in)
    tx_ref = make_tx_ref("spaces")
    redirect_url = settings.PAYMENT_REDIRECT_URL or os.getenv("PAYMENT_REDIRECT_URL")
    if not redirect_url:
        forwarded_proto = request.headers.get("x-forwarded-proto", request.url.scheme)
        forwarded_host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        public_host = forwarded_host or request.url.netloc
        redirect_url = f"{forwarded_proto}://{public_host}/payment/callback"
    payload = build_checkout_payload(
        amount=payment.amount,
        currency=payment.currency,
        email=user.email,
        tx_ref=tx_ref,
        booking_id=str(payment.booking_id),
        user_id=str(user.id),
        redirect_url=redirect_url,
        customer_name=user.full_name or user.email,
    )

    try:
        gateway_response = create_flutterwave_payment(payload)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network failure path
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Flutterwave payment initialization failed: {exc}") from exc

    if gateway_response.get("status") != "success":
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=gateway_response.get("message", "Flutterwave rejected the payment initialization"))

    payment.transaction_ref = tx_ref
    payment.gateway_response = gateway_response
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


@router.get("/mine", response_model=list[PaymentRead])
async def read_my_payments(user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    """Every payment the signed-in guest made, across their bookings."""
    return await list_payments_for_guest(session, str(user.id))


@router.get("/{payment_id}", response_model=PaymentRead)
async def read_payment(payment_id: uuid.UUID, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    """Fetch one payment. Only the booking's guest or an admin may read it.

    Ownership is resolved through the related booking, since a payment row has
    no user column of its own.
    """
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
async def payment_webhook(request: Request, session: AsyncSession = Depends(get_async_session)):
    """Handle gateway callback events and update the local payment row."""
    raw_body = await request.body()
    payload = json.loads(raw_body) if raw_body else {}
    signature = request.headers.get("verif-hash") or request.headers.get("X-Webhook-Secret")
    webhook_secret = settings.PAYMENT_WEBHOOK_SECRET or os.getenv("PAYMENT_WEBHOOK_SECRET")

    if not webhook_secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Webhook verification is temporarily unavailable")
    if not verify_webhook_signature(raw_body, signature, webhook_secret):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid webhook signature")

    event_data = payload.get("data", {}) if isinstance(payload, dict) else {}
    tx_ref = event_data.get("tx_ref")
    if not tx_ref:
        return {"status": "ignored", "message": "No transaction reference in webhook payload"}

    payment = await get_payment_by_transaction_ref(session, tx_ref)
    if not payment:
        return {"status": "ignored", "message": "Payment not found for transaction reference"}

    status_value = str(event_data.get("status", ""))
    await apply_payment_status(session, payment, status_value, payload)

    return {"status": "ok", "payment_id": str(payment.id), "payment_status": payment.status.value}


async def apply_payment_status(session: AsyncSession, payment: Payment, status_value: str, payload: dict) -> Payment:
    """Apply a gateway status once; repeated callbacks must not duplicate wallet holds."""
    normalized = str(status_value).lower()

    if normalized in {"successful", "success", "completed", "paid"}:
        if payment.status not in {PaymentStatus.success, PaymentStatus.refunded}:
            payment.status = PaymentStatus.success
            payment.paid_at = datetime.now(timezone.utc)
            await hold_booking_wallet_funds(session, payment.booking_id)
    elif normalized in {"failed", "failure", "cancelled", "canceled"}:
        if payment.status == PaymentStatus.pending:
            payment.status = PaymentStatus.failed
            payment.paid_at = None
    elif normalized in {"refunded", "chargeback", "reverse"}:
        if payment.status != PaymentStatus.refunded:
            was_successful = payment.status == PaymentStatus.success
            payment.status = PaymentStatus.refunded
            payment.paid_at = None
            if was_successful:
                await reverse_booking_wallet_hold(session, payment.booking_id)
    else:
        payment.status = PaymentStatus.pending

    payment.gateway_response = payload
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


@router.post("/{payment_id}/verify", response_model=PaymentRead)
async def verify_payment_status(
    payment_id: uuid.UUID,
    transaction_id: str = Query(..., min_length=1),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Verify an initiated Flutterwave transaction against the provider."""
    payment = await get_payment_by_id(session, payment_id)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    booking = await get_booking_by_id(session, payment.booking_id)
    if not booking or (str(booking.user_id) != str(user.id) and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    try:
        result = verify_flutterwave_transaction(transaction_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Flutterwave verification failed: {exc}") from exc

    data = result.get("data", {}) if isinstance(result, dict) else {}
    if data:
        data_tx_ref = data.get("tx_ref")
        if payment.transaction_ref and data_tx_ref and data_tx_ref != payment.transaction_ref:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction reference mismatch")

    return await apply_payment_status(session, payment, str(data.get("status", "")), result)


@callback_router.get("/payment/callback")
@callback_router.get("/api/v1/payments/callback")
async def payment_callback(
    status_value: str | None = Query(default=None, alias="status"),
    tx_ref: str | None = Query(default=None),
    transaction_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_async_session),
):
    """Handle Flutterwave's browser redirect after checkout.

    Browser redirects are not authenticated API requests, so completion is
    made safe by looking up the local transaction reference and independently
    verifying the gateway's transaction id.
    """
    if not tx_ref:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing tx_ref")
    if not transaction_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing transaction_id")

    payment = await get_payment_by_transaction_ref(session, tx_ref)
    if not payment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")

    try:
        result = verify_flutterwave_transaction(transaction_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Flutterwave verification failed: {exc}") from exc

    data = result.get("data", {}) if isinstance(result, dict) else {}
    data_tx_ref = data.get("tx_ref")
    if data_tx_ref and data_tx_ref != payment.transaction_ref:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Transaction reference mismatch")

    verified_status = str(data.get("status") or status_value or "")
    await apply_payment_status(session, payment, verified_status, result)
    return {"status": "ok", "payment_id": str(payment.id), "payment_status": payment.status.value}
