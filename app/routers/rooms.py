from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.room import create_room as crud_create_room
from ..database import get_async_session
from ..schemas.room import RoomCreate, RoomResponse

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.post("/json", response_model=RoomResponse)
async def list_room_json(
    room_in: RoomCreate,
    property_id: str,
    session: AsyncSession = Depends(get_async_session),
):
    return await crud_create_room(session=session, room_data=room_in, property_id=property_id)


@router.post("/upload", response_model=RoomResponse)
async def list_room_with_files(
    title: str = Form(...),
    description: str = Form(...),
    price_per_night: float = Form(...),
    property_id: str = Form(...),
    images: List[UploadFile] = File(...),
    session: AsyncSession = Depends(get_async_session),
):
    if len(images) < 3:
        raise HTTPException(status_code=400, detail="You must provide at least 3 images.")
    if len(images) > 7:
        raise HTTPException(status_code=400, detail="You cannot upload more than 7 images.")

    saved_image_urls = [f"https://your-storage-provider.com/uploads/{image.filename}" for image in images]
    validated_payload = RoomCreate(
        title=title,
        description=description,
        price_per_night=price_per_night,
        images=saved_image_urls,
    )
    return await crud_create_room(session=session, room_data=validated_payload, property_id=property_id)
