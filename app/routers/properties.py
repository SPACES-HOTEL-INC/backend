"""Property endpoints: public search, owner CRUD and admin verification.

Creation is a multipart form rather than JSON because it accepts image uploads.
Filters are optional and additive; each one that is supplied narrows the result
set further.
"""

import json
import os
import shutil
import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.dependencies import get_current_user, require_admin, require_host
from ..core.cloudinary import upload_image_to_cloudinary
from ..crud.property import create_property, deactivate_property, get_property_by_id, list_host_properties, list_properties, update_property
from ..database import get_async_session
from ..models.property import Property
from ..models.room import Room
from ..schemas.property import PropertyCreate, PropertyRead, PropertyUpdate

router = APIRouter(prefix="/api/v1/properties", tags=["properties"])

# Local fallback target for images when Cloudinary is unavailable or fails.
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
    """Public property search, paginated.

    Price filters apply to room rates, not the property itself, so this joins
    to Room. `distinct` keeps properties from appearing once per matching room.
    Soft-deleted (inactive) properties are always excluded.
    """
    query = select(Property).where(Property.is_active == True)

    # Case-insensitive matching, with whitespace tolerated on the type filter
    # because it usually arrives from a free-text query.
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

    # Offset/limit paging rather than keyset: the result set is small enough
    # that deep pages are not a practical concern.
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
    # Note: this includes inactive properties, so an owner can see their
    # soft-deleted listings here even though search omits them.
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
    """Fetch one active property. Inactive properties are reported as 404."""
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
    user=Depends(require_host),
    session: AsyncSession = Depends(get_async_session),
):
    """Create a property, uploading any attached images.

    Image handling is best-effort per file: a failure on one image is skipped
    rather than failing the whole request, since a listing without photos is
    still useful. Contact details are stored as one combined string, and the
    amenity field accepts either JSON or a comma-separated list.
    """
    # Accept JSON first, then fall back to a comma-separated list so the same
    # form field works for both the API client and a plain HTML form.
    try:
        parsed_amenities = json.loads(amenities) if amenities else []
    except Exception:
        parsed_amenities = [a.strip() for a in amenities.split(",") if a.strip()] if amenities else []

    normalized_type = property_type.strip().lower() if property_type else property_type

    # Upload images to Cloudinary (preferred) or fallback to local storage
    saved_image_urls: list[str] = []
    for img in images:
        if not img.filename:
            continue
        try:
            # Attempt Cloudinary upload (async wrapper)
            url = await upload_image_to_cloudinary(img.file, folder="spaces/properties")
            if url:
                saved_image_urls.append(url)
                continue
        except Exception:
            # Fall back to saving locally if Cloudinary fails
            pass

        # Local fallback
        try:
            file_ext = os.path.splitext(img.filename)[1]
            # Random name avoids collisions and stops a client from choosing
            # the on-disk path.
            unique_filename = f"{uuid.uuid4().hex}{file_ext}"
            file_path = os.path.join(UPLOAD_DIR, unique_filename)

            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(img.file, buffer)

            saved_image_urls.append(f"/static/uploads/properties/{unique_filename}")
        except Exception:
            # If even fallback fails, skip the image
            continue

    # The first uploaded image doubles as the cover shown in listings.
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

    # The schema's name field has drifted over time (hotel_name/name/title), so
    # the payload fills in whichever aliases the current schema declares
    # instead of hardcoding one of them.
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

    # Owner comes from the token so a property cannot be created for someone else.
    return await create_property(session, str(user.id), property_in)


@router.put("/{property_id}", response_model=PropertyRead)
async def update_property_endpoint(
    property_id: uuid.UUID,
    property_in: PropertyUpdate,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Replace a property's editable fields. Owner only."""
    property_obj = await get_property_by_id(session, str(property_id))
    # A non-owner gets 404 rather than 403, so the endpoint does not confirm
    # that someone else's property exists.
    if not property_obj or str(property_obj.owner_id) != str(user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found or not owned")
    return await update_property(session, property_obj, property_in)


@router.delete("/{property_id}", response_model=PropertyRead)
async def delete_property_endpoint(
    property_id: uuid.UUID,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Soft-delete a property. Owner or admin only.

    The row is kept and flagged inactive so existing bookings and reviews keep
    their references.
    """
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
    """Mark a property as verified. Admin only.

    The flag is set directly here rather than through the CRUD layer because
    verification is a one-field admin action, not a general update.
    """
    property_obj = await get_property_by_id(session, str(property_id))
    if not property_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    property_obj.is_verified = True
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


@router.get("/featured", response_model=list[PropertyRead])
async def list_featured_properties(
    limit: int = Query(4, ge=1, le=50), session: AsyncSession = Depends(get_async_session)
):
    """
    Returns top-rated active properties ordered by `avg_rating`.

    NOTE: this route is declared after `/{property_id}`, so FastAPI matches the
    UUID path first and a request for `/featured` fails to parse as a UUID.
    Move this declaration above `/{property_id}` to fix.
    """
    query = select(Property).where(Property.is_active == True).order_by(Property.avg_rating.desc()).limit(limit)
    result = await session.execute(query)
    return result.scalars().all()