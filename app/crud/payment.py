"""Database operations for payments.

NOTE: nothing currently marks a payment as successful. There is no gateway
callback route yet, so every payment stays "pending".
"""

import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.booking import Booking
from ..models.payment import Payment, PaymentStatus
from ..schemas.payment import PaymentCreate, PaymentUpdate


async def get_payment_by_id(session: AsyncSession, payment_id: str | uuid.UUID) -> Payment | None:
    """Fetch one payment by id, or None."""
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def list_payments_for_booking(session: AsyncSession, booking_id: str | uuid.UUID) -> list[Payment]:
    """Payment attempts against one booking. More than one is possible if a
    guest retries after a failure."""
    result = await session.execute(select(Payment).where(Payment.booking_id == booking_id))
    return result.scalars().all()


async def list_payments_for_guest(session: AsyncSession, guest_id: str | uuid.UUID) -> list[Payment]:
    """Payments across every booking this guest made.

    Joins through Booking because a payment references a booking, not a user.
    """
    result = await session.execute(
        select(Payment)
        .join(Booking, Payment.booking_id == Booking.id)
        .where(Booking.user_id == guest_id)
    )
    return result.scalars().all()


async def create_payment(session: AsyncSession, payment_in: PaymentCreate) -> Payment:
    """Insert a payment record in the pending state.

    The schema carries booking_id as a string, so it is coerced to a UUID before
    insertion. The caller checks the amount against the booking.
    """
    data = payment_in.model_dump()
    data["booking_id"] = uuid.UUID(data["booking_id"])
    payment = Payment(**data)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_payment(session: AsyncSession, payment: Payment, update_in: PaymentUpdate) -> Payment:
    """Apply a partial update, typically from a gateway callback."""
    for field, value in update_in.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment
