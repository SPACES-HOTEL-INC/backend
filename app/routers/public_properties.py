"""Unauthenticated property endpoints.

Shares the `/api/v1/properties` prefix with the authenticated properties
router. Registered after it, so this `/{property_id}/rooms` path does not
shadow anything in that router.
"""

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
    """Rooms in one active property. No authentication required.

    Inactive properties are reported as 404 so soft-deleted listings are not
    browsable.
    """
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or not property_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return await get_rooms_for_property(session, property_id)
