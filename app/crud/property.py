from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.property import Property
from ..schemas.property import PropertyCreate, PropertyUpdate


async def get_property_by_id(session: AsyncSession, property_id: str) -> Property | None:
    result = await session.execute(select(Property).where(Property.id == property_id))
    return result.scalar_one_or_none()


async def list_properties(session: AsyncSession) -> list[Property]:
    result = await session.execute(select(Property).where(Property.is_active == True))
    return result.scalars().all()


async def create_property(session: AsyncSession, host_id: str, property_in: PropertyCreate) -> Property:
    property_data = property_in.model_dump(exclude_unset=True)
    if property_data.get("hotel_name") is None and property_data.get("name"):
        property_data["hotel_name"] = property_data["name"]
    if property_data.get("images"):
        property_data["images"] = [str(url) for url in property_data["images"]]
    if property_data.get("contact") is None:
        property_data["contact"] = property_data.get("address") or ""
    property_obj = Property(owner_id=host_id, **property_data)
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def update_property(session: AsyncSession, property_obj: Property, update_in: PropertyUpdate) -> Property:
    update_data = update_in.model_dump(exclude_unset=True)
    if "hotel_name" in update_data and update_data["hotel_name"] is not None:
        property_obj.hotel_name = update_data["hotel_name"]
        del update_data["hotel_name"]
    if "name" in update_data and update_data["name"] is not None:
        property_obj.hotel_name = update_data["name"]
        del update_data["name"]
    for field, value in update_data.items():
        if value is not None:
            setattr(property_obj, field, value)
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def deactivate_property(session: AsyncSession, property_obj: Property) -> Property:
    property_obj.is_active = False
    session.add(property_obj)
    await session.commit()
    await session.refresh(property_obj)
    return property_obj


async def list_host_properties(session: AsyncSession, host_id: str) -> list[Property]:
    result = await session.execute(select(Property).where(Property.owner_id == host_id, Property.is_active == True))
    return result.scalars().all()
