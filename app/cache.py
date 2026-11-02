"""Redis helper functions for the FastAPI app."""

import json
from typing import Any

import redis.asyncio as redis

from .config import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)


async def get_cache(key: str) -> Any | None:
    """Fetch a JSON value from Redis; returns None when missing."""
    value = await redis_client.get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


async def set_cache(key: str, value: Any, ttl: int | None = None) -> None:
    """Store a JSON-serialisable value in Redis."""
    payload = json.dumps(value, default=_json_default)
    await redis_client.set(key, payload, ex=ttl or settings.REDIS_TTL_SECONDS)


async def delete_cache(key: str) -> None:
    """Delete a single key from Redis."""
    await redis_client.delete(key)


async def delete_pattern(prefix: str) -> None:
    """Delete every key matching the provided prefix."""
    keys = await redis_client.keys(f"{prefix}*")
    if keys:
        await redis_client.delete(*keys)


def _json_default(value: Any) -> Any:
    """Convert non-JSON-native objects to a safe Redis payload."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "hex"):
        return str(value)
    return str(value)
