from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_host
from ..crud.property import create_property, deactivate_property, get_property_by_id, list_host_properties, list_properties, update_property
from ..database import get_async_session
from ..schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])


@router.get("/", response_model=list[PropertyRead])
async def search_properties(
    city: str | None = Query(None),
    property_type: str | None = Query(None),
    min_price: float | None = Query(None),
    max_price: float | None = Query(None),
    page: int = 1,
    limit: int = 10,
    session: AsyncSession = Depends(get_async_session),
):
    return await list_properties(session)


@router.get("/{property_id}", response_model=PropertyRead)
async def read_property(property_id: str, session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, property_id)
    if not property_obj or not property_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return property_obj


@router.post("/", response_model=PropertyRead)
async def create_property_endpoint(property_in: PropertyCreate, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    return await create_property(session, str(user.id), property_in)


@router.put("/{property_id}", response_model=PropertyRead)
async def update_property_endpoint(property_id: str, property_in: PropertyUpdate, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, property_id)
    if not property_obj or str(property_obj.host_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await update_property(session, property_obj, property_in)


@router.delete("/{property_id}", response_model=PropertyRead)
async def delete_property_endpoint(property_id: str, user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, property_id)
    if not property_obj or (str(property_obj.host_id) != str(user.id) and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await deactivate_property(session, property_obj)


@router.get("/mine", response_model=list[PropertyRead])
async def read_my_properties(user=Depends(require_host), session: AsyncSession = Depends(get_async_session)):
    return await list_host_properties(session, str(user.id))
