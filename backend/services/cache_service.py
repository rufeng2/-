"""Versioned Redis caches for retrieval and completed answers."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from redis.asyncio import Redis

from backend.config import settings
from backend.services.observability import CACHE_EVENTS
from backend.utils.logger import logger


class CacheService:
    def __init__(self):
        self._redis: Redis | None = None

    @property
    def redis(self) -> Redis:
        if self._redis is None:
            self._redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    @staticmethod
    def _digest(payload: dict) -> str:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def version(self, namespace: str) -> int:
        try:
            value = await self.redis.get(f"rag:version:{namespace}")
            return int(value or 1)
        except Exception as exc:
            logger.warning("Cache version lookup failed: %s", exc)
            return 1

    async def bump_version(self, namespace: str) -> None:
        try:
            await self.redis.incr(f"rag:version:{namespace}")
        except Exception as exc:
            logger.warning("Cache version bump failed: %s", exc)

    async def build_key(self, cache: str, payload: dict, versions: tuple[str, ...] = ()) -> str:
        enriched = dict(payload)
        for namespace in versions:
            enriched[f"version:{namespace}"] = await self.version(namespace)
        return f"rag:{cache}:{self._digest(enriched)}"

    async def get_json(self, cache: str, key: str) -> Any | None:
        if not settings.RAG_CACHE_ENABLED:
            return None
        try:
            value = await self.redis.get(key)
            CACHE_EVENTS.labels(cache=cache, outcome="hit" if value else "miss").inc()
            return json.loads(value) if value else None
        except Exception as exc:
            CACHE_EVENTS.labels(cache=cache, outcome="error").inc()
            logger.warning("Redis cache read failed: %s", exc)
            return None

    async def set_json(self, cache: str, key: str, value: Any, ttl: int) -> None:
        if not settings.RAG_CACHE_ENABLED:
            return
        try:
            await self.redis.set(key, json.dumps(value, ensure_ascii=False), ex=ttl)
            CACHE_EVENTS.labels(cache=cache, outcome="write").inc()
        except Exception as exc:
            CACHE_EVENTS.labels(cache=cache, outcome="error").inc()
            logger.warning("Redis cache write failed: %s", exc)


cache_service = CacheService()
