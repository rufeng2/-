"""Liveness and dependency-aware readiness endpoints."""
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from backend.services.dependency_health import dependency_health


router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("/live")
async def live():
    return {"status": "ok"}


@router.get("/ready")
async def ready():
    snapshot = await dependency_health.snapshot(max_age_seconds=0)
    ready_state = snapshot.postgres and snapshot.redis and snapshot.minio
    payload = {
        "status": "ready" if ready_state else "not_ready",
        "dependencies": snapshot.public_payload(),
    }
    return JSONResponse(payload, status_code=200 if ready_state else 503)
