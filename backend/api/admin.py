"""
管理员 API：用户管理、部门管理、权限管理、系统统计
"""
import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func

from backend.db.session import get_db
from backend.db.models import (
    User, Department, Document, DocumentChunk, ChunkPermission,
    Conversation, Message, Feedback,
)
from backend.schemas.user import AdminUserCreate, UserInfo
from backend.schemas.common import ApiResponse
from backend.utils.auth import require_admin, hash_password
from backend.utils.logger import logger

router = APIRouter(prefix="/api/admin", tags=["管理后台"])


# ====================== 用户管理 ======================

@router.get("/users", response_model=ApiResponse)
async def list_users(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """用户列表"""
    stmt = select(User).order_by(User.created_at.desc())
    result = await db.execute(stmt)
    users = result.scalars().all()

    return ApiResponse(data=[
        UserInfo(
            id=str(u.id), username=u.username,
            display_name=u.display_name, email=u.email,
            role=u.role, department=str(u.department),
            is_active=u.is_active,
        )
        for u in users
    ])


@router.post("/users", response_model=ApiResponse)
async def create_user(
    req: AdminUserCreate,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """管理员创建用户"""
    stmt = select(User).where(User.username == req.username)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return ApiResponse(code=400, msg="用户名已存在")

    user = User(
        username=req.username,
        password=hash_password(req.password),
        display_name=req.display_name or req.username,
        department=req.department,
        role=req.role,
    )
    db.add(user)
    await db.flush()
    logger.info(f"Admin created user: {req.username}")
    return ApiResponse(msg="用户创建成功")


@router.delete("/users/{user_id}", response_model=ApiResponse)
async def delete_user(
    user_id: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除用户"""
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的用户ID")

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return ApiResponse(code=404, msg="用户不存在")

    await db.delete(user)
    logger.info(f"Admin deleted user: {user.username}")
    return ApiResponse(msg="用户已删除")


@router.put("/users/{user_id}/toggle-status", response_model=ApiResponse)
async def toggle_user_status(
    user_id: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """启用/禁用用户"""
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的用户ID")

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return ApiResponse(code=404, msg="用户不存在")

    user.is_active = not user.is_active
    status = "启用" if user.is_active else "禁用"
    logger.info(f"Admin {status} user: {user.username}")
    return ApiResponse(msg=f"用户已{status}")


# ====================== 部门管理 ======================

@router.get("/departments", response_model=ApiResponse)
async def list_departments(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """部门列表"""
    stmt = select(Department).order_by(Department.name)
    result = await db.execute(stmt)
    depts = result.scalars().all()

    return ApiResponse(data=[
        {
            "id": str(d.id),
            "name": d.name,
            "parent_id": str(d.parent_id) if d.parent_id else "",
            "description": d.description,
        }
        for d in depts
    ])


@router.post("/departments", response_model=ApiResponse)
async def create_department(
    name: str = Query(...),
    description: str = Query(""),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """创建部门"""
    stmt = select(Department).where(Department.name == name)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        return ApiResponse(code=400, msg="部门已存在")

    dept = Department(name=name, description=description)
    db.add(dept)
    await db.flush()
    return ApiResponse(msg="部门创建成功", data={"id": str(dept.id)})


@router.delete("/departments/{dept_id}", response_model=ApiResponse)
async def delete_department(
    dept_id: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """删除部门"""
    try:
            did = uuid.UUID(dept_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的部门ID")

    stmt = select(Department).where(Department.id == did)
    result = await db.execute(stmt)
    dept = result.scalar_one_or_none()
    if not dept:
        return ApiResponse(code=404, msg="部门不存在")

    await db.delete(dept)
    return ApiResponse(msg="部门已删除")


# ====================== 文档权限 ======================

@router.post("/permissions/document/{doc_id}", response_model=ApiResponse)
async def set_document_permissions(
    doc_id: str,
    department_ids: list[str],
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    设置文档的可见部门
    只有指定部门的用户才能检索到该文档的内容
    """
    try:
        doc_uuid = uuid.UUID(doc_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的文档ID")

    # 获取文档的所有 chunk
    chunk_stmt = select(DocumentChunk.id).where(DocumentChunk.document_id == doc_uuid)
    chunk_result = await db.execute(chunk_stmt)
    chunk_ids = chunk_result.scalars().all()

    if not chunk_ids:
        return ApiResponse(code=404, msg="文档尚未解析或没有 chunk")

    if not department_ids:
        return ApiResponse(code=400, msg="请至少指定一个可见部门")

    # 清除旧权限
    for cid in chunk_ids:
        await db.execute(
            delete(ChunkPermission).where(ChunkPermission.chunk_id == cid)
        )

    # 设置新权限
    for cid in chunk_ids:
        for did_str in department_ids:
            try:
                did = uuid.UUID(did_str)
                cp = ChunkPermission(chunk_id=cid, department_id=did)
                db.add(cp)
            except (ValueError, TypeError):
                continue

    await db.flush()
    logger.info(f"Permissions set for doc {doc_id}: {len(department_ids)} depts")
    return ApiResponse(msg=f"已为 {len(chunk_ids)} 个文档块设置权限")


@router.get("/permissions/document/{doc_id}", response_model=ApiResponse)
async def get_document_permissions(
    doc_id: str,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查看文档当前的可见部门"""
    try:
        doc_uuid = uuid.UUID(doc_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的文档ID")

    chunk_stmt = (
        select(DocumentChunk.id)
        .where(DocumentChunk.document_id == doc_uuid)
        .limit(1)
    )
    chunk_result = await db.execute(chunk_stmt)
    first_chunk = chunk_result.scalar_one_or_none()

    if not first_chunk:
        return ApiResponse(code=404, msg="文档尚未解析")

    perm_stmt = (
        select(Department.name, Department.id)
        .join(ChunkPermission, ChunkPermission.department_id == Department.id)
        .where(ChunkPermission.chunk_id == first_chunk)
        .distinct()
    )
    perm_result = await db.execute(perm_stmt)
    depts = perm_result.all()

    return ApiResponse(data=[
        {"id": str(d[1]), "name": d[0]} for d in depts
    ])


# ====================== 用户部门分配 ======================

@router.put("/users/{user_id}/department", response_model=ApiResponse)
async def set_user_department(
    user_id: str,
    department_id: str = Query(...),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """设置用户所属部门"""
    try:
        uid = uuid.UUID(user_id)
        did = uuid.UUID(department_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的ID")

    stmt = select(User).where(User.id == uid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return ApiResponse(code=404, msg="用户不存在")

    user.department = str(did)
    await db.flush()
    return ApiResponse(msg=f"用户 {user.username} 部门已更新")


# ====================== 系统统计 ======================

@router.get("/stats", response_model=ApiResponse)
async def get_stats(
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """系统统计数据"""
    # 用户数
    user_count = (await db.execute(select(func.count(User.id)))).scalar() or 0
    # 文档数
    doc_count = (await db.execute(select(func.count(Document.id)))).scalar() or 0
    # 索引文档数
    indexed_count = (
        await db.execute(
            select(func.count(Document.id)).where(Document.status == "indexed")
        )
    ).scalar() or 0
    # 对话数
    conv_count = (
        await db.execute(select(func.count(Conversation.id)))
    ).scalar() or 0
    # 消息数
    msg_count = (
        await db.execute(select(func.count(Message.id)))
    ).scalar() or 0
    # 部门数
    dept_count = (
        await db.execute(select(func.count(Department.id)))
    ).scalar() or 0
    # 反馈统计
    positive_fb = (
        await db.execute(
            select(func.count(Message.id)).where(Message.feedback == 1)
        )
    ).scalar() or 0
    negative_fb = (
        await db.execute(
            select(func.count(Message.id)).where(Message.feedback == -1)
        )
    ).scalar() or 0

    return ApiResponse(data={
        "users": user_count,
        "documents": doc_count,
        "indexed_documents": indexed_count,
        "conversations": conv_count,
        "messages": msg_count,
        "departments": dept_count,
        "feedback_positive": positive_fb,
        "feedback_negative": negative_fb,
    })


# ====================== 对话历史查询 ======================

@router.get("/history", response_model=ApiResponse)
async def get_all_history(
    limit: int = Query(100, ge=1, le=500),
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """查看所有用户最近的对话"""
    stmt = (
        select(Message)
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    msgs = result.scalars().all()

    # 获取用户名
    user_ids = set(str(m.id) for m in msgs)
    user_map = {}
    if user_ids:
        users = await db.execute(
            select(User.id, User.username).where(User.id.in_(user_ids))
        )
        for uid, uname in users:
            user_map[str(uid)] = uname

    return ApiResponse(data=[
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content[:300],
            "feedback": m.feedback,
            "created_at": str(m.created_at),
        }
        for m in msgs
    ])
