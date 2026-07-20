import asyncio
import sys

sys.path.insert(0, r'd:/spaces bk/backend')

from app.crud.user import authenticate_user
from app.database import AsyncSessionLocal


async def main() -> None:
    async with AsyncSessionLocal() as session:
        user = await authenticate_user(session, 'test@example.com', 'secret')
        print('user-none' if user is None else user.email)


asyncio.run(main())
