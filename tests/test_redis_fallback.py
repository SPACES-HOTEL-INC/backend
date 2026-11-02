import asyncio
import socket

from app.cache import build_redis_client, delete_pattern, get_cache, set_cache


def test_invalid_redis_url_does_not_crash_import_path():
    assert build_redis_client("${{ Redis.REDIS_PRIVATE_URL }}") is None
    assert build_redis_client("not-a-url") is None


def test_get_cache_returns_none_when_redis_unavailable(monkeypatch):
    async def boom(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr("app.cache.redis_client.get", boom)

    assert asyncio.run(get_cache("missing-key")) is None


def test_set_cache_does_not_raise_when_redis_unavailable(monkeypatch):
    async def boom(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr("app.cache.redis_client.set", boom)

    asyncio.run(set_cache("demo", {"hello": "world"}))


def test_delete_pattern_handles_redis_errors(monkeypatch):
    async def boom(*args, **kwargs):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr("app.cache.redis_client.keys", boom)

    asyncio.run(delete_pattern("properties:search"))
