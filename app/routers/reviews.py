import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin, require_host
from ..crud.booking import BookingStatus, get_booking_by_id
from ..crud.property import get_property_by_id
from ..crud.review import create_review, delete_review, get_review_by_booking, get_review_by_id, list_reviews_for_property, update_review
from ..database import get_async_session
from ..schemas.review import HostResponseUpdate, ReviewCreate, ReviewRead, ReviewUpdate

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewRead, status_code=status.HTTP_201_CREATED)
async def create_review_endpoint(review_in: ReviewCreate, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    booking = await get_booking_by_id(session, review_in.booking_id)
    if not booking or str(booking.user_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found or not authorized")
    if booking.status != BookingStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking must be completed before leaving a review")
    existing = await get_review_by_booking(session, review_in.booking_id)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already exists for this booking")
    return await create_review(session, review_in, str(user.id))


@router.get("/property/{property_id}", response_model=list[ReviewRead])
async def read_property_reviews(property_id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):
    return await list_reviews_for_property(session, str(property_id))


@router.put("/{review_id}", response_model=ReviewRead)
async def update_review_endpoint(review_id: uuid.UUID, review_in: ReviewUpdate, user=Depends(get_current_user), session: AsyncSession = Depends(get_async_session)):
    review = await get_review_by_id(session, review_id)
    if not review or str(review.guest_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found or not authorized")
    return await update_review(session, review, review_in)


@router.post("/{review_id}/host-response", response_model=ReviewRead)
async def host_response(review_id: uuid.UUID, review_in: HostResponseUpdate, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    review = await get_review_by_id(session, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    property_obj = await get_property_by_id(session, str(review.property_id))
    if not property_obj or str(property_obj.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to respond")
    review.host_response = review_in.host_response
    session.add(review)
    await session.commit()
    await session.refresh(review)
    return review


@router.delete("/{review_id}")
async def delete_review_endpoint(review_id: uuid.UUID, user=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    review = await get_review_by_id(session, review_id)
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    await delete_review(session, review)
    return {"detail": "Review deleted"}
