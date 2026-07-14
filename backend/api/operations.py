"""Production operations: audit review, privacy controls and evaluation baselines."""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import AuditLog, Conversation, EvaluationRun, Feedback, Message, User
from backend.db.session import get_db
from backend.schemas.common import ApiResponse
from backend.utils.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/operations", tags=["production-operations"])


@router.get("/audit-logs", response_model=ApiResponse)
async def audit_logs(
    limit: int = Query(100, ge=1, le=1000),
    action: str = Query(""),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        statement = statement.where(AuditLog.action == action.upper())
    rows = (await db.execute(statement)).scalars().all()
    return ApiResponse(data=[{
        "id": str(row.id), "username": row.username, "role": row.role,
        "action": row.action, "resource_type": row.resource_type,
        "resource_id": row.resource_id, "path": row.path,
        "status_code": row.status_code, "ip_address": row.ip_address,
        "request_id": row.request_id, "created_at": str(row.created_at),
    } for row in rows])


@router.get("/privacy/export", response_model=ApiResponse)
async def export_my_data(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    db_user = (await db.execute(select(User).where(User.username == user["username"]))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(404, "User not found")
    conversations = (await db.execute(select(Conversation).where(Conversation.user_id == db_user.id))).scalars().all()
    ids = [item.id for item in conversations]
    messages = (await db.execute(select(Message).where(Message.conversation_id.in_(ids)))).scalars().all() if ids else []
    return ApiResponse(data={
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "profile": {"username": db_user.username, "display_name": db_user.display_name, "email": db_user.email, "department": db_user.department},
        "conversations": [{"id": str(item.id), "title": item.title, "created_at": str(item.created_at)} for item in conversations],
        "messages": [{"conversation_id": str(item.conversation_id), "role": item.role, "content": item.content, "created_at": str(item.created_at)} for item in messages],
    })


@router.delete("/privacy/me", response_model=ApiResponse)
async def delete_my_data(user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.get("role") == "admin":
        raise HTTPException(400, "Administrator accounts cannot self-delete")
    db_user = (await db.execute(select(User).where(User.username == user["username"]))).scalar_one_or_none()
    if not db_user:
        raise HTTPException(404, "User not found")
    await db.execute(delete(Feedback).where(Feedback.user_id == db_user.id))
    await db.execute(delete(Conversation).where(Conversation.user_id == db_user.id))
    db_user.username = f"deleted-{str(db_user.id)[:12]}"
    db_user.display_name = "Deleted user"
    db_user.email = ""
    db_user.password = "disabled"
    db_user.department = ""
    db_user.is_active = False
    return ApiResponse(msg="Personal profile was anonymized and conversation data deleted")


@router.post("/evaluation/{run_id}/baseline", response_model=ApiResponse)
async def set_baseline(
    run_id: str,
    name: str = Query("production"),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        run_uuid = uuid.UUID(run_id)
    except ValueError as exc:
        raise HTTPException(400, "Invalid run id") from exc
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == run_uuid))).scalar_one_or_none()
    if not run or run.status != "completed":
        raise HTTPException(404, "Completed evaluation run not found")
    await db.execute(EvaluationRun.__table__.update().where(EvaluationRun.baseline_name == name).values(is_baseline=False))
    run.is_baseline = True
    run.baseline_name = name
    return ApiResponse(msg="Evaluation baseline saved", data={"id": str(run.id), "name": name, "metrics": run.metrics})


@router.get("/evaluation/compare", response_model=ApiResponse)
async def compare_evaluations(
    run_id: str,
    baseline: str = Query("production"),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    current = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == uuid.UUID(run_id)))).scalar_one_or_none()
    base = (await db.execute(select(EvaluationRun).where(EvaluationRun.is_baseline.is_(True), EvaluationRun.baseline_name == baseline))).scalar_one_or_none()
    if not current or not base:
        raise HTTPException(404, "Evaluation run or baseline not found")
    numeric = set(current.metrics or {}) & set(base.metrics or {})
    delta = {key: round(float(current.metrics[key]) - float(base.metrics[key]), 6) for key in numeric if isinstance(current.metrics[key], (int, float)) and isinstance(base.metrics[key], (int, float))}
    return ApiResponse(data={"baseline_id": str(base.id), "current_id": str(current.id), "baseline": base.metrics, "current": current.metrics, "delta": delta})