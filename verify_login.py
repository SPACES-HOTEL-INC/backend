import asyncio
import sys

import httpx

sys.path.insert(0, r'd:/spaces bk/backend')


async def main() -> None:
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(
            'http://127.0.0.1:8000/api/v1/auth/login',
            json={'email': 'test@example.com', 'password': 'secret'},
        )
        print(response.status_code)
        print(response.text)


asyncio.run(main())
