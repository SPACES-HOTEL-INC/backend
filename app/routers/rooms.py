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
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Property not found"
        )
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
    if property_id is not None:
        await _verify_property_ownership(property_id, user, session)
        return await get_rooms_for_property(session, property_id)

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
    await _verify_property_ownership(property_id, user, session)
    return await crud_create_room(session=session, room_data=room_in, property_id=property_id)


@router.post("/json", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def list_room_json(
    room_in: RoomCreate,
    property_id: uuid.UUID,
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
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
    limit: int = Query(6, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    """
    Public rooms listing. Returns rooms for active properties, optionally filtered by city.
    Each item includes room fields plus parent property metadata: hotel_name, city, state, address, avg_rating.
    """
    query = select(Room, Property).join(Property, Room.property_id == Property.id).where(Property.is_active == True)
    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    # Order by property rating (desc) then room price (asc)
    query = query.order_by(Property.avg_rating.desc(), Room.price_per_night.asc()).limit(limit)

    result = await session.execute(query)
    rows = result.all()

    out = []
    for room_obj, prop in rows:
        out.append(
            {
                "id": str(room_obj.id),
                "property_id": str(room_obj.property_id),
                "title": room_obj.title,
                "description": room_obj.description,
                "price_per_night": room_obj.price_per_night,
                "images": room_obj.images,
                "hotel_name": prop.hotel_name,
                "city": prop.city,
                "state": prop.state,
                "address": prop.address,
                "avg_rating": prop.avg_rating,
            }
        )

    return out