from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.payment import Payment, PaymentStatus
from ..schemas.payment import PaymentCreate, PaymentUpdate


async def get_payment_by_id(session: AsyncSession, payment_id: str) -> Payment | None:
    result = await session.execute(select(Payment).where(Payment.id == payment_id))
    return result.scalar_one_or_none()


async def list_payments_for_booking(session: AsyncSession, booking_id: str) -> list[Payment]:
    result = await session.execute(select(Payment).where(Payment.booking_id == booking_id))
    return result.scalars().all()


async def list_payments_for_guest(session: AsyncSession, guest_id: str) -> list[Payment]:
    result = await session.execute(
        select(Payment).join(Payment.booking).where(Payment.booking.has(guest_id=guest_id))
    )
    return result.scalars().all()


async def create_payment(session: AsyncSession, payment_in: PaymentCreate) -> Payment:
    payment = Payment(**payment_in.model_dump())
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment


async def update_payment(session: AsyncSession, payment: Payment, update_in: PaymentUpdate) -> Payment:
    for field, value in update_in.model_dump(exclude_unset=True).items():
        setattr(payment, field, value)
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return payment
