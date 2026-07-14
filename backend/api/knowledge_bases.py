"""Knowledge base management API."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Department, Document, KnowledgeBase, User
from backend.db.session import get_db
from backend.schemas.common import ApiResponse
from backend.schemas.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from backend.utils.auth import get_current_user

router = APIRouter(prefix="/api/knowledge-bases", tags=["知识库"])


async def _db_user(user: dict, db: AsyncSession) -> User | None:
    return (await db.execute(
        select(User).where(User.username == user["username"])
    )).scalar_one_or_none()


def _access_filter(user: dict, db_user: User):
    if user.get("role") == "admin":
        return True
    department_id = select(Department.id).where(
        Department.name == db_user.department
    ).scalar_subquery()
    return or_(
        KnowledgeBase.visibility.in_(["public", "internal"]),
        KnowledgeBase.owner_id == db_user.id,
        KnowledgeBase.department_id == department_id,
    )


@router.get("", response_model=ApiResponse)
async def list_knowledge_bases(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_user = await _db_user(user, db)
    if not db_user:
        return ApiResponse(code=401, msg="用户不存在")
    count_subquery = (
        select(func.count(Document.id))
        .where(Document.knowledge_base_id == KnowledgeBase.id)
        .correlate(KnowledgeBase)
        .scalar_subquery()
    )
    stmt = (
        select(KnowledgeBase, count_subquery.label("document_count"))
        .where(_access_filter(user, db_user))
        .order_by(KnowledgeBase.created_at.asc())
    )
    rows = (await db.execute(stmt)).all()
    return ApiResponse(data=[{
        "id": str(kb.id),
        "name": kb.name,
        "description": kb.description,
        "visibility": kb.visibility,
        "department_id": str(kb.department_id) if kb.department_id else "",
        "owner_id": str(kb.owner_id) if kb.owner_id else "",
        "document_count": count,
        "created_at": str(kb.created_at),
    } for kb, count in rows])


@router.post("", response_model=ApiResponse)
async def create_knowledge_base(
    request: KnowledgeBaseCreate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if request.visibility not in {"public", "internal", "confidential"}:
        return ApiResponse(code=400, msg="无效的可见范围")
    if (await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.name == request.name.strip())
    )).scalar_one_or_none():
        return ApiResponse(code=400, msg="知识库名称已存在")
    db_user = await _db_user(user, db)
    if not db_user:
        return ApiResponse(code=401, msg="用户不存在")
    department_id = None
    if request.department_id:
        try:
            department_id = uuid.UUID(request.department_id)
        except ValueError:
            return ApiResponse(code=400, msg="无效的部门ID")
    kb = KnowledgeBase(
        name=request.name.strip(),
        description=request.description.strip(),
        visibility=request.visibility,
        owner_id=db_user.id,
        department_id=department_id,
    )
    db.add(kb)
    await db.flush()
    return ApiResponse(msg="知识库创建成功", data={"id": str(kb.id)})


@router.put("/{knowledge_base_id}", response_model=ApiResponse)
async def update_knowledge_base(
    knowledge_base_id: str,
    request: KnowledgeBaseUpdate,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        kb_id = uuid.UUID(knowledge_base_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的知识库ID")
    db_user = await _db_user(user, db)
    stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    if user.get("role") != "admin":
        stmt = stmt.where(KnowledgeBase.owner_id == db_user.id)
    kb = (await db.execute(stmt)).scalar_one_or_none()
    if not kb:
        return ApiResponse(code=404, msg="知识库不存在或无权修改")
    values = request.model_dump(exclude_unset=True)
    if "visibility" in values and values["visibility"] not in {"public", "internal", "confidential"}:
        return ApiResponse(code=400, msg="无效的可见范围")
    if values.get("department_id"):
        try:
            values["department_id"] = uuid.UUID(values["department_id"])
        except ValueError:
            return ApiResponse(code=400, msg="无效的部门ID")
    elif "department_id" in values:
        values["department_id"] = None
    for key, value in values.items():
        setattr(kb, key, value)
    return ApiResponse(msg="知识库更新成功")


@router.delete("/{knowledge_base_id}", response_model=ApiResponse)
async def delete_knowledge_base(
    knowledge_base_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        kb_id = uuid.UUID(knowledge_base_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的知识库ID")
    db_user = await _db_user(user, db)
    stmt = select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    if user.get("role") != "admin":
        stmt = stmt.where(KnowledgeBase.owner_id == db_user.id)
    kb = (await db.execute(stmt)).scalar_one_or_none()
    if not kb:
        return ApiResponse(code=404, msg="知识库不存在或无权删除")
    count = (await db.execute(
        select(func.count(Document.id)).where(Document.knowledge_base_id == kb.id)
    )).scalar_one()
    if count:
        return ApiResponse(code=409, msg="知识库中仍有文档，请先移动或删除文档")
    await db.delete(kb)
    return ApiResponse(msg="知识库删除成功")

