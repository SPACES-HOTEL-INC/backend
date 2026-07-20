from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.review import Review
from ..schemas.review import ReviewCreate, ReviewUpdate


async def get_review_by_id(session: AsyncSession, review_id: str) -> Review | None:
    result = await session.execute(select(Review).where(Review.id == review_id))
    return result.scalar_one_or_none()


async def get_review_by_booking(session: AsyncSession, booking_id: str) -> Review | None:
    result = await session.execute(select(Review).where(Review.booking_id == booking_id))
    return result.scalar_one_or_none()


async def list_reviews_for_property(session: AsyncSession, property_id: str) -> list[Review]:
    result = await session.execute(select(Review).where(Review.property_id == property_id))
    return result.scalars().all()


async def create_review(session: AsyncSession, review_in: ReviewCreate, guest_id: str) -> Review:
    review = Review(guest_id=guest_id, **review_in.model_dump())
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def update_review(session: AsyncSession, review: Review, review_in: ReviewUpdate) -> Review:
    for field, value in review_in.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


async def delete_review(session: AsyncSession, review: Review) -> None:
    await session.delete(review)
    await session.commit()
