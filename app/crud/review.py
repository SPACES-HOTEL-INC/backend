"""Database operations for reviews.

Property rating figures are cached on the property row, so every write here
calls `_refresh_property_ratings` to keep them accurate.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.property import Property
from ..models.review import Review
from ..schemas.review import ReviewCreate, ReviewUpdate


async def get_review_by_id(session: AsyncSession, review_id: str) -> Review | None:
    """Fetch one review by id, or None."""
    result = await session.execute(select(Review).where(Review.id == review_id))
    return result.scalar_one_or_none()


async def get_review_by_booking(session: AsyncSession, booking_id: str) -> Review | None:
    """The review left for a booking, if any. Used to block double reviews."""
    result = await session.execute(select(Review).where(Review.booking_id == booking_id))
    return result.scalar_one_or_none()


async def list_reviews_for_property(session: AsyncSession, property_id: str) -> list[Review]:
    """Every review left against one property."""
    result = await session.execute(select(Review).where(Review.property_id == property_id))
    return result.scalars().all()


async def create_review(session: AsyncSession, review_in: ReviewCreate, guest_id: str) -> Review:
    """Insert a review, then recompute the property's cached rating.

    The caller is responsible for setting `property_id`; it is not part of
    ReviewCreate because it is derived from the booking, not client-supplied.
    """
    review = Review(guest_id=guest_id, **review_in.model_dump())
    session.add(review)
    await session.commit()
    await session.refresh(review)

    await _refresh_property_ratings(session, str(review.property_id))
    await session.refresh(review)
    return review


async def update_review(session: AsyncSession, review: Review, review_in: ReviewUpdate) -> Review:
    """Edit a review's rating or comment, then refresh the cached average."""
    property_id = str(review.property_id)
    for field, value in review_in.model_dump(exclude_unset=True).items():
        setattr(review, field, value)
    session.add(review)
    await session.commit()
    await session.refresh(review)

    await _refresh_property_ratings(session, property_id)
    await session.refresh(review)
    return review


async def delete_review(session: AsyncSession, review: Review) -> None:
    """Remove a review and bring the property's cached average back in line."""
    property_id = str(review.property_id)
    await session.delete(review)
    await session.commit()

    await _refresh_property_ratings(session, property_id)


async def _refresh_property_ratings(session: AsyncSession, property_id: str) -> None:
    """Recompute avg_rating and total_reviews for one property.

    Averaging in the database keeps the stored figures exact. Both fall back to
    zero when the last review is deleted, since AVG over no rows is NULL.
    """
    result = await session.execute(
        select(func.avg(Review.rating), func.count(Review.id))
        .where(Review.property_id == property_id)
    )
    row = result.one_or_none()
    avg_rating = float(row[0]) if row and row[0] is not None else 0.0
    total_reviews = int(row[1]) if row and row[1] is not None else 0

    property_obj = await session.get(Property, property_id)
    if property_obj:
        # Rounded to one decimal for display.
        property_obj.avg_rating = round(avg_rating, 1)
        property_obj.total_reviews = total_reviews
        session.add(property_obj)
        await session.commit()
