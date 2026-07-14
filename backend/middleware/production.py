"""Request IDs, Prometheus metrics, Redis rate limits, concurrency and audit logging."""
import asyncio
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
from prometheus_client import Counter, Histogram
from redis.asyncio import Redis

from backend.config import settings
from backend.db.models import AuditLog
from backend.db.session import AsyncSessionLocal
from backend.utils.logger import logger

REQUESTS = Counter("rag_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("rag_http_request_duration_seconds", "HTTP request latency", ["method", "path"])
ERRORS = Counter("rag_http_errors_total", "Unhandled HTTP errors", ["path"])
EXPENSIVE_PATHS = ("/api/chat/send", "/api/documents/upload", "/api/evaluation/runs")
_expensive = asyncio.Semaphore(settings.MAX_CONCURRENT_EXPENSIVE_REQUESTS)


def _identity(request: Request) -> tuple[str, str]:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = jwt.decode(auth[7:], settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return str(payload.get("sub", "anonymous")), str(payload.get("role", ""))
        except JWTError:
            pass
    forwarded = request.headers.get("x-forwarded-for", "")
    return (forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown"), "")


async def _allow_request(identity: str) -> tuple[bool, int]:
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        minute = int(time.time() // 60)
        day = int(time.time() // 86400)
        minute_key = f"limit:minute:{identity}:{minute}"
        day_key = f"limit:day:{identity}:{day}"
        pipe = redis.pipeline()
        pipe.incr(minute_key)
        pipe.expire(minute_key, 120)
        pipe.incr(day_key)
        pipe.expire(day_key, 172800)
        minute_count, _, day_count, _ = await pipe.execute()
        allowed = minute_count <= settings.RATE_LIMIT_PER_MINUTE and day_count <= settings.DAILY_REQUEST_QUOTA
        return allowed, max(0, settings.RATE_LIMIT_PER_MINUTE - int(minute_count))
    except Exception as exc:
        logger.warning(f"Rate limiter unavailable, failing open: {exc}")
        return True, settings.RATE_LIMIT_PER_MINUTE
    finally:
        await redis.aclose()


async def production_middleware(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    identity, role = _identity(request)
    path = request.url.path
    allowed, remaining = await _allow_request(identity)
    if not allowed:
        return JSONResponse({"code": 429, "msg": "Request rate or daily quota exceeded"}, status_code=429, headers={"Retry-After": "60", "X-Request-ID": request_id})

    status_code = 500
    try:
        if any(path.startswith(prefix) for prefix in EXPENSIVE_PATHS):
            async with _expensive:
                response = await call_next(request)
        else:
            response = await call_next(request)
        status_code = response.status_code
    except Exception:
        ERRORS.labels(path=path).inc()
        logger.exception(f"Unhandled request error request_id={request_id} path={path}")
        raise
    finally:
        elapsed = time.perf_counter() - started
        REQUESTS.labels(method=request.method, path=path, status=str(status_code)).inc()
        LATENCY.labels(method=request.method, path=path).observe(elapsed)

    response.headers["X-Request-ID"] = request_id
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and path != "/api/login":
        try:
            async with AsyncSessionLocal() as db:
                db.add(AuditLog(
                    username=identity,
                    role=role,
                    action=request.method,
                    resource_type=path.split("/")[2] if len(path.split("/")) > 2 else "api",
                    resource_id=path.rsplit("/", 1)[-1],
                    path=path,
                    status_code=status_code,
                    ip_address=request.client.host if request.client else "",
                    request_id=request_id,
                ))
                await db.commit()
        except Exception as exc:
            logger.warning(f"Audit write failed request_id={request_id}: {exc}")
    return response