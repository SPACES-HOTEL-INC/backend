"""Room endpoints for hosts (create/list) and guests (public browse).

Every write goes through `_verify_property_ownership`, so a host can only touch
rooms on a property they own. The public routes return a flattened shape of room
plus parent property fields, built by hand because there is no schema for it.
"""

import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cloudinary import upload_image_to_cloudinary
from ..core.dependencies import require_host
from ..crud.property import get_property_by_id, list_host_properties
from ..crud.room import create_room as crud_create_room, get_rooms_for_property
from ..database import get_async_session
from ..models.room import Room
from ..models.property import Property
from ..schemas.room import RoomCreate, RoomResponse

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


async def _verify_property_ownership(
    property_id: uuid.UUID, user, session: AsyncSession
) -> None:
    """Assert the caller owns an active property.

    Returns nothing; it raises the appropriate 404/400/403 so each caller can
    stay a one-liner.
    """
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )
    # Rooms cannot be added to a soft-deleted property.
    if not property_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Property is not active"
        )
    if str(property_obj.owner_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to add rooms to this property",
        )


@router.get("/", response_model=list[RoomResponse])
async def list_rooms_for_host(
    property_id: uuid.UUID | None = Query(default=None),
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """List the host's rooms, optionally scoped to one of their properties."""
    if property_id is not None:
        await _verify_property_ownership(property_id, user, session)
        return await get_rooms_for_property(session, property_id)

    # No filter: gather the host's property ids first, then query rooms in one
    # round trip rather than per property.
    host_properties = await list_host_properties(session, str(user.id))
    if not host_properties:
        return []

    property_ids = [property_obj.id for property_obj in host_properties]
    result = await session.execute(
        select(Room).where(Room.property_id.in_(property_ids)).order_by(Room.title.asc())
    )
    return result.scalars().all()


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room_json(
    room_in: RoomCreate,
    property_id: uuid.UUID = Query(...),
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a room from a JSON body. `property_id` is a query parameter here."""
    await _verify_property_ownership(property_id, user, session)
    return await crud_create_room(session=session, room_data=room_in, property_id=property_id)


@router.post("/json", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def list_room_json(
    room_in: RoomCreate,
    property_id: uuid.UUID,
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """Duplicate of POST `/` with `property_id` in the body instead of the
    query string. Kept for clients that already post the full object."""
    await _verify_property_ownership(property_id, user, session)
    return await crud_create_room(session=session, room_data=room_in, property_id=property_id)


@router.post("/upload", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def list_room_with_files(
    title: str = Form(...),
    description: str = Form(...),
    price_per_night: float = Form(...),
    property_id: uuid.UUID = Form(...),
    images: list[UploadFile] = File(...),
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a room from a multipart form with image uploads.

    The image count is bounded at 3-7 so listings stay consistent and the upload
    cost per room is predictable. Cloudinary is the only storage path here, with
    no local fallback, so a failed upload fails the request.
    """
    if len(images) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide at least 3 images.",
        )
    if len(images) > 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot upload more than 7 images.",
        )

    await _verify_property_ownership(property_id, user, session)

    saved_image_urls = []
    for image in images:
        url = await upload_image_to_cloudinary(image.file, folder="spaces/rooms")
        saved_image_urls.append(url)

    # Reuse the JSON schema so validation is identical on both create paths.
    validated_payload = RoomCreate(
        title=title,
        description=description,
        price_per_night=price_per_night,
        images=saved_image_urls,
    )
    return await crud_create_room(
        session=session, room_data=validated_payload, property_id=property_id
    )


@router.get("/public", response_model=list[dict])
async def list_public_rooms(
    city: str | None = Query(None),
    # Default to Home-friendly limit=8
    limit: int = Query(8, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Public rooms listing. Returns rooms for active properties, optionally filtered by city.
    Each item includes room fields plus parent property metadata: hotel_name, city, state, address, avg_rating.

    Sorted by property rating then price, and the join to Property excludes
    soft-deleted listings.
    """
    query = (
        select(
            Room.id,
            Room.property_id,
            Room.title,
            Room.description,
            Room.price_per_night,
            Room.images,
            Property.hotel_name,
            Property.city,
            Property.state,
            Property.address,
            Property.avg_rating,
            Property.total_reviews,
        )
        .join(Property, Room.property_id == Property.id)
        .where(Property.is_active == True)
    )
    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    # Order by property rating (desc) then room price (asc)
    query = query.order_by(Property.avg_rating.desc(), Room.price_per_night.asc()).limit(limit)

    result = await session.execute(query)
    rows = result.all()

    # Flattened into plain dicts: the public response shape is not modelled by a
    # schema, so ids are stringified here.
    out = []
    for (
        room_id,
        property_id,
        title,
        description,
        price_per_night,
        images,
        hotel_name,
        city_val,
        state_val,
        address_val,
        avg_rating,
        total_reviews,
    ) in rows:
        out.append(
            {
                "id": str(room_id),
                "property_id": str(property_id),
                "title": title,
                "description": description,
                "price_per_night": price_per_night,
                "images": images,
                "hotel_name": hotel_name,
                "city": city_val,
                "state": state_val,
                "address": address_val,
                "avg_rating": avg_rating,
                "total_reviews": total_reviews,
            }
        )

    return out


@router.get("/search", response_model=list[dict])
async def search_public_rooms(
    city: str | None = Query(None),
    min_price: float | None = Query(None, gt=0),
    max_price: float | None = Query(None, gt=0),
    property_type: str | None = Query(None),
    # Default per-page search limit = 12
    limit: int = Query(12, ge=1, le=200),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Search rooms publicly with optional filters: city, min_price, max_price, property_type.
    Returns rooms joined with parent property metadata.

    Same response shape as `/public`; this variant adds price and type filters.
    """
    query = (
        select(
            Room.id,
            Room.property_id,
            Room.title,
            Room.description,
            Room.price_per_night,
            Room.images,
            Property.hotel_name,
            Property.city,
            Property.state,
            Property.address,
            Property.avg_rating,
            Property.total_reviews,
            Property.property_type,
        )
        .join(Property, Room.property_id == Property.id)
        .where(Property.is_active == True)
    )

    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    if property_type:
        query = query.where(func.lower(Property.property_type) == property_type.strip().lower())
    if min_price is not None:
        query = query.where(Room.price_per_night >= min_price)
    if max_price is not None:
        query = query.where(Room.price_per_night <= max_price)

    query = query.order_by(Property.avg_rating.desc(), Room.price_per_night.asc()).limit(limit)

    result = await session.execute(query)
    rows = result.all()

    out = []
    for (
        room_id,
        property_id,
        title,
        description,
        price_per_night,
        images,
        hotel_name,
        city_val,
        state_val,
        address_val,
        avg_rating,
        total_reviews,
        property_type_val,
    ) in rows:
        out.append(
            {
                "id": str(room_id),
                "property_id": str(property_id),
                "title": title,
                "description": description,
                "price_per_night": price_per_night,
                "images": images,
                "hotel_name": hotel_name,
                "city": city_val,
                "state": state_val,
                "address": address_val,
                "avg_rating": avg_rating,
                "total_reviews": total_reviews,
                "property_type": property_type_val,
            }
        )

    return out


@router.get("/public/{room_id}", response_model=dict)
async def get_public_room(room_id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):
    """
    Get a single public room by id joined with its parent property details.
    """
    query = (
        select(
            Room.id,
            Room.property_id,
            Room.title,
            Room.description,
            Room.price_per_night,
            Room.images,
            Property.hotel_name,
            Property.address,
            Property.city,
            Property.state,
            Property.country,
            Property.amenities,
            Property.cancellation_policy,
            Property.avg_rating,
            Property.total_reviews,
            Property.contact,
            Property.images.label("property_images"),
        )
        .join(Property, Room.property_id == Property.id)
        .where(Room.id == room_id)
        .where(Property.is_active == True)
    )

    result = await session.execute(query)
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    (
        room_id_val,
        property_id,
        title,
        description,
        price_per_night,
        images,
        hotel_name,
        address_val,
        city_val,
        state_val,
        country_val,
        amenities_val,
        cancellation_policy,
        avg_rating,
        total_reviews,
        contact_val,
        property_images,
    ) = row

    # Ensure JSON fields are arrays
    images_list = images if isinstance(images, list) else (images or [])
    prop_images_list = property_images if isinstance(property_images, list) else (property_images or [])
    amenities_list = amenities_val if isinstance(amenities_val, list) else (amenities_val or [])

    return {
        "id": str(room_id_val),
        "property_id": str(property_id),
        "title": title,
        "description": description,
        "price_per_night": price_per_night,
        "images": images_list,
        "hotel_name": hotel_name,
        "address": address_val,
        "city": city_val,
        "state": state_val,
        "country": country_val,
        "amenities": amenities_list,
        "cancellation_policy": cancellation_policy,
        "avg_rating": avg_rating,
        "total_reviews": total_reviews,
        "contact": contact_val,
        "property_images": prop_images_list,
    }