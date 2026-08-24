import json
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin, require_host
from ..crud.property import create_property, deactivate_property, get_property_by_id, list_host_properties, list_properties, update_property
from ..database import get_async_session
from ..models.property import Property
from ..models.room import Room
from ..schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])

UPLOAD_DIR = "static/uploads/properties"
os.makedirs(UPLOAD_DIR, exist_ok=True)


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
        query = query.where(func.lower(Property.property_type) == property_type.strip().lower())
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


@router.get("/mine", response_model=list[PropertyRead])
async def read_my_properties(
    user=Depends(get_current_user), 
    session: AsyncSession = Depends(get_async_session)
):
    """
    Fetch all properties owned by the currently authenticated user.
    Uses get_current_user to prevent 403 Forbidden errors when fetching owned branches.
    """
    try:
        properties = await list_host_properties(session, str(user.id))
        return properties
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch properties: {str(e)}"
        )


@router.get("/{property_id}", response_model=PropertyRead)
async def read_property(property_id: uuid.UUID, session: AsyncSession = Depends(get_async_session)):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or not property_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return property_obj


@router.post("/", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
async def create_property_endpoint(
    name: str = Form(...),
    property_type: str = Form(...),
    address: str = Form(...),
    city: str | None = Form(None),
    state: str | None = Form(None),
    country: str | None = Form("Nigeria"),
    phone: str | None = Form(None),
    email: str | None = Form(None),
    description: str | None = Form(None),
    amenities: str | None = Form("[]"),
    images: list[UploadFile] = File(default=[]),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    try:
        parsed_amenities = json.loads(amenities) if amenities else []
    except Exception:
        parsed_amenities = [a.strip() for a in amenities.split(",") if a.strip()] if amenities else []

    normalized_type = property_type.strip().lower() if property_type else property_type

    # Save uploaded images to disk
    saved_image_urls: list[str] = []
    for img in images:
        if img.filename:
            file_ext = os.path.splitext(img.filename)[1]
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)

            saved_image_urls.append(f"/static/uploads/properties/{unique_filename}")

    primary_image_url = saved_image_urls[0] if saved_image_urls else None

    # Format phone and email into single contact string
    contact_parts = [c.strip() for c in [phone, email] if c and c.strip()]
    contact_info = " | ".join(contact_parts) if contact_parts else None

    create_data = {
        "hotel_name": name,
        "property_type": normalized_type,
        "address": address,
        "city": city,
        "state": state,
        "country": country,
        "contact": contact_info,
        "description": description,
        "amenities": parsed_amenities,
    }

    # Dynamically match schema attributes (title, name, hotel_name)
    schema_fields = getattr(PropertyCreate, "__fields__", getattr(PropertyCreate, "model_fields", {}))
    if "title" in schema_fields:
        create_data["title"] = name
    if "name" in schema_fields:
        create_data["name"] = name
    if "image_url" in schema_fields:
        create_data["image_url"] = primary_image_url
    if "images" in schema_fields:
        create_data["images"] = saved_image_urls

    property_in = PropertyCreate(**create_data)

    return await create_property(session, str(user.id), property_in)


@router.put("/{property_id}", response_model=PropertyRead)
async def update_property_endpoint(
    property_id: uuid.UUID,
    property_in: PropertyUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or str(property_obj.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await update_property(session, property_obj, property_in)


@router.delete("/{property_id}", response_model=PropertyRead)
async def delete_property_endpoint(
    property_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj or (str(property_obj.owner_id) != str(user.id) and not getattr(user, 'is_admin', False)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await deactivate_property(session, property_obj)


@router.patch("/{property_id}/verify", response_model=PropertyRead)
async def verify_property_endpoint(
    property_id: uuid.UUID,
    user=Depends(require_admin),
    session: AsyncSession = Depends(get_async_session),
):
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    property_obj.is_verified = True
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj