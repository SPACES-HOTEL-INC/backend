"""Database operations for properties.

`create_property` and `update_property` absorb several client payload shapes:
`name` for `hotel_name`, and separate `phone`/`email` that are merged into the
single `contact` column.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.property import Property
from ..schemas.property import PropertyCreate, PropertyUpdate


async def get_property_by_id(session: AsyncSession, property_id: str) -> Property | None:
    """Fetch one property by id, or None."""
    result = await session.execute(select(Property).where(Property.id == property_id))
    return result.scalar_one_or_none()


async def list_properties(session: AsyncSession) -> list[Property]:
    """Every active property, public listing. Deactivated ones are excluded."""
    result = await session.execute(select(Property).where(Property.is_active == True))
    return result.scalars().all()


async def create_property(session: AsyncSession, host_id: str, property_in: PropertyCreate) -> Property:
    """Create a property owned by `host_id`.

    contact is required in the database, so if the client sent phone/email
    instead, they are joined into it; failing that it falls back to the address
    so the insert cannot violate a NOT NULL constraint.
    """
    property_data = property_in.model_dump(exclude_unset=True)

    # Clean up legacy or alias fields
    if not property_data.get("hotel_name") and property_data.get("name"):
        property_data["hotel_name"] = property_data.pop("name")
    else:
        property_data.pop("name", None)

    # Pop non-column contact fields and consolidate into contact
    phone = property_data.pop("phone", None)
    email = property_data.pop("email", None)

    if not property_data.get("contact"):
        contact_parts = [c.strip() for c in [phone, email] if c and isinstance(c, str) and c.strip()]
        if contact_parts:
            property_data["contact"] = " | ".join(contact_parts)
        else:
            property_data["contact"] = property_data.get("address") or ""

    # Ensure HttpUrl objects in images list are converted to strings
    if property_data.get("images"):
        property_data["images"] = [str(url) for url in property_data["images"]]

    property_obj = Property(owner_id=host_id, **property_data)
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def update_property(session: AsyncSession, property_obj: Property, update_in: PropertyUpdate) -> Property:
    """Apply a partial update.

    Fields needing a transform (hotel_name, contact, images) are handled first
    and removed from the dict; the rest are set directly, skipping None so an
    omitted field is not overwritten with null.
    """
    update_data = update_in.model_dump(exclude_unset=True)

    # Handle hotel_name fallbacks
    if "hotel_name" in update_data and update_data["hotel_name"] is not None:
        property_obj.hotel_name = update_data["hotel_name"]
        del update_data["hotel_name"]
    if "name" in update_data:
        if update_data["name"] is not None:
            property_obj.hotel_name = update_data["name"]
        del update_data["name"]

    # Handle phone/email pops and set contact string
    phone = update_data.pop("phone", None)
    email = update_data.pop("email", None)
    if phone or email:
        contact_parts = [c.strip() for c in [phone, email] if c and isinstance(c, str) and c.strip()]
        if contact_parts:
            property_obj.contact = " | ".join(contact_parts)

    # Stringify images list if provided
    if "images" in update_data and update_data["images"] is not None:
        property_obj.images = [str(url) for url in update_data["images"]]
        del update_data["images"]

    # Assign remaining fields safely
    for field, value in update_data.items():
        if value is not None and hasattr(property_obj, field):
            setattr(property_obj, field, value)

    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def deactivate_property(session: AsyncSession, property_obj: Property) -> Property:
    """Soft-delete a property.

    Sets is_active False instead of removing the row, so bookings, payments and
    reviews keep a valid reference.
    """
    property_obj.is_active = False
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def list_host_properties(session: AsyncSession, host_id: str) -> list[Property]:
    """Active properties owned by one host, for the dashboard."""
    result = await session.execute(select(Property).where(Property.owner_id == host_id, Property.is_active == True))
    return result.scalars().all()