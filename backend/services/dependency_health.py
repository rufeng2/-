"""Dependency probes and capability-based degradation policy."""
from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import time
from urllib.parse import urlparse

from sqlalchemy import text

from backend.config import settings
from backend.db.session import engine
from backend.services.cache_service import cache_service


@dataclass(frozen=True)
class DependencySnapshot:
    postgres: bool
    redis: bool
    rabbitmq: bool
    minio: bool

    def public_payload(self) -> dict[str, bool]:
        return asdict(self)


def capability_available(snapshot: DependencySnapshot, capability: str) -> bool:
    if not snapshot.postgres:
        return False
    if not snapshot.redis and capability not in {"documents.read", "chat.read"}:
        return False
    if not snapshot.rabbitmq and capability in {"documents.upload", "documents.reindex"}:
        return False
    if not snapshot.minio and capability in {"documents.upload", "documents.download", "chat.image"}:
        return False
    return True


async def _tcp_probe(host: str, port: int) -> bool:
    try:
        _reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=1.0)
        writer.close()
        await writer.wait_closed()
        return True
    except Exception:
        return False


class DependencyHealthService:
    def __init__(self) -> None:
        self._cached: DependencySnapshot | None = None
        self._cached_at = 0.0

    async def snapshot(self, max_age_seconds: float = 2.0) -> DependencySnapshot:
        now = time.monotonic()
        if self._cached and now - self._cached_at <= max_age_seconds:
            return self._cached

        async def postgres_probe() -> bool:
            try:
                async with engine.connect() as connection:
                    await asyncio.wait_for(connection.execute(text("SELECT 1")), timeout=1.5)
                return True
            except Exception:
                return False

        async def redis_probe() -> bool:
            try:
                return bool(await asyncio.wait_for(cache_service.redis.ping(), timeout=1.0))
            except Exception:
                return False

        rabbit = urlparse(settings.RABBITMQ_URL)
        minio_endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "").split("/", 1)[0]
        minio_host, _, minio_port = minio_endpoint.partition(":")
        postgres_ok, redis_ok, rabbit_ok, minio_ok = await asyncio.gather(
            postgres_probe(),
            redis_probe(),
            _tcp_probe(rabbit.hostname or "rabbitmq", rabbit.port or 5672),
            _tcp_probe(minio_host or "minio", int(minio_port or 9000)) if settings.USE_MINIO else asyncio.sleep(0, result=True),
        )
        self._cached = DependencySnapshot(postgres_ok, redis_ok, rabbit_ok, minio_ok)
        self._cached_at = now
        return self._cached


dependency_health = DependencyHealthService()
