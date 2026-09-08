"""Redis cache helpers.

All forecast reads go through this layer. When Redis is unavailable the helpers
degrade to a no-op so the API keeps serving from the in-process dataset.
"""

import json
import logging
from typing import Any

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_client: redis.Redis | None = None
_disabled = False


def get_client() -> redis.Redis | None:
    global _client
    if _disabled:
        return None
    if _client is None:
        _client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    return _client


async def cache_get(key: str) -> Any | None:
    client = get_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
    except Exception as exc:  # noqa: BLE001 - cache must never break a request
        logger.warning("redis get failed for %s: %s", key, exc)
        return None
    return json.loads(raw) if raw else None


async def cache_set(key: str, value: Any, ttl: int | None = None) -> None:
    client = get_client()
    if client is None:
        return
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl or settings.cache_ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis set failed for %s: %s", key, exc)


async def cache_delete_prefix(prefix: str) -> None:
    client = get_client()
    if client is None:
        return
    try:
        async for key in client.scan_iter(match=f"{prefix}*"):
            await client.delete(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis purge failed for %s: %s", prefix, exc)


async def close_cache() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
