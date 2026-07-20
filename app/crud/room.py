import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.room import Room
from ..schemas.room import RoomCreate


async def create_room(session: AsyncSession, room_data: RoomCreate, property_id: str | uuid.UUID) -> Room:
    db_room = Room(
        property_id=property_id,
        title=room_data.title,
        description=room_data.description,
        price_per_night=room_data.price_per_night,
        images=[str(url) for url in room_data.images],
    )
    session.add(db_room)
    await session.commit()
    await session.refresh(db_room)
    return db_room


async def get_room_by_id(session: AsyncSession, room_id: uuid.UUID) -> Optional[Room]:
    result = await session.execute(select(Room).where(Room.id == room_id))
    return result.scalar_one_or_none()