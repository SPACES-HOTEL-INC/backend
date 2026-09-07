import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_async_session
from ..crud.property import get_property_by_id
from ..crud.room import get_rooms_for_property
from ..schemas.room import RoomResponse

router = APIRouter(prefix="/api/v1/properties", tags=["public-properties"])


@router.get("/{property_id}/rooms", response_model=list[RoomResponse])
async def public_list_rooms_for_property(
    property_id: uuid.UUID, session: AsyncSession = Depends(get_async_session)
):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or not property_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return await get_rooms_for_property(session, property_id)
