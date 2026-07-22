import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin, require_host
from ..crud.property import create_property, deactivate_property, get_property_by_id, list_host_properties, list_properties, update_property
from ..database import get_async_session
from ..models.property import Property
from ..models.room import Room
from ..schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])


@router.get("/", response_model=list[PropertyRead])
async def search_properties(
    city: str | None = Query(None),
    property_type: str | None = Query(None),
    min_price: float | None = Query(None, gt=0),
    max_price: float | None = Query(None, gt=0),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
):
    query = select(Property).where(Property.is_active == True)

    if city:
        query = query.where(func.lower(Property.city) == city.lower())
    if property_type:
        query = query.where(Property.property_type == property_type)
    if min_price is not None or max_price is not None:
        query = query.join(Room, Property.id == Room.property_id)
        if min_price is not None:
            query = query.where(Room.price_per_night >= min_price)
        if max_price is not None:
            query = query.where(Room.price_per_night <= max_price)
        query = query.distinct()

    query = query.offset((page - 1) * limit).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()


@router.get("/{property_id}", response_model=PropertyRead)
async def read_property(property_id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or not property_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return property_obj


@router.post("/", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property_endpoint(property_in: PropertyCreate, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    return await create_property(session, str(user.id), property_in)


@router.put("/{property_id}", response_model=PropertyRead)
async def update_property_endpoint(property_id: uuid.UUID, property_in: PropertyUpdate, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or str(property_obj.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await update_property(session, property_obj, property_in)


@router.delete("/{property_id}", response_model=PropertyRead)
async def delete_property_endpoint(property_id: uuid.UUID, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or (str(property_obj.owner_id) != str(user.id) and not user.is_admin):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await deactivate_property(session, property_obj)


@router.get("/mine", response_model=list[PropertyRead])
async def read_my_properties(user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    return await list_host_properties(session, str(user.id))


@router.patch("/{property_id}/verify", response_model=PropertyRead)
async def verify_property_endpoint(property_id: uuid.UUID, user=Depends(require_admin), session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    property_obj.is_verified = True
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj
