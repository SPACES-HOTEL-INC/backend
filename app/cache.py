"""Redis helper functions for the FastAPI app."""

import json
import logging
from typing import Any

import redis.asyncio as redis

from .config import settings

logger = logging.getLogger(__name__)

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=2,
    health_check_interval=30,
)


async def get_cache(key: str) -> Any | None:
    """Fetch a JSON value from Redis; returns None when missing or unreachable."""
    try:
        value = await redis_client.get(key)
    except Exception as exc:  # pragma: no cover - exercised by unit tests via monkeypatch
        logger.warning("Redis cache read failed for %s: %s", key, exc)
        return None

    if value is None:
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


async def set_cache(key: str, value: Any, ttl: int | None = None) -> None:
    """Store a JSON-serialisable value in Redis; silently skip on failure."""
    try:
        payload = json.dumps(value, default=_json_default)
        await redis_client.set(key, payload, ex=ttl or settings.REDIS_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Redis cache write failed for %s: %s", key, exc)


async def delete_cache(key: str) -> None:
    """Delete a single key from Redis; silently skip on failure."""
    try:
        await redis_client.delete(key)
    except Exception as exc:
        logger.warning("Redis cache delete failed for %s: %s", key, exc)


async def delete_pattern(prefix: str) -> None:
    """Delete every key matching the provided prefix; silently skip on failure."""
    try:
        keys = await redis_client.keys(f"{prefix}*")
        if keys:
            await redis_client.delete(*keys)
    except Exception as exc:
        logger.warning("Redis cache key cleanup failed for prefix %s: %s", prefix, exc)


def _json_default(value: Any) -> Any:
    """Convert non-JSON-native objects to a safe Redis payload."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "hex"):
        return str(value)
    return str(value)
