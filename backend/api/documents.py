"""
文档管理 API: 上传、列表、删除、解析
"""
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func

from backend.db.session import get_db
from backend.db.models import Document, DocumentChunk, KnowledgeBase, User, Department
from backend.schemas.document import DocumentInfo, DocumentUpdateRequest
from backend.schemas.common import ApiResponse
from backend.utils.auth import get_current_user
from backend.security.rbac import require_permission
from backend.services.indexing_service import index_document
from backend.tasks.parse_task import parse_document
from backend.services.storage_service import storage_service
from backend.config import settings
from backend.utils.logger import logger
from backend.security.file_security import scan_with_clamav, validate_file

router = APIRouter(prefix="/api/documents", tags=["文档管理"])

# 允许的文件类型
ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".xlsx",
    ".pptx", ".txt", ".md", ".csv",
    ".jpg", ".jpeg", ".png", ".bmp", ".tiff",
}


@router.post("/upload", response_model=ApiResponse)
async def upload_document(
    file: UploadFile = File(...),
    visibility: str = Query("internal"),
    department_id: Optional[str] = Query(None),
    knowledge_base_id: Optional[str] = Query(None),
    chunk_template: str = Query("general"),
    user: dict = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
):
    """上传文档"""
    # 校验文件类型
    filename = file.filename or "unknown"
    ext = Path(filename).suffix.lower()
    if ext in {".doc", ".xls", ".ppt"}:
        return ApiResponse(code=400, msg="旧版 Office 格式暂不直接解析，请另存为 DOCX、XLSX 或 PPTX 后上传")
    if ext not in ALLOWED_EXTENSIONS:
        return ApiResponse(code=400, msg=f"不支持的文件类型: {ext}")

    try:
        saved_path, file_size = await storage_service.save_upload(
            file, ext, settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        )
    except ValueError as exc:
        if str(exc) == "upload_too_large":
            return ApiResponse(code=413, msg=f"文件不能超过 {settings.MAX_UPLOAD_SIZE_MB} MB")
        raise
    file_path = Path(saved_path)
    try:
        validate_file(str(file_path), ext)
        scan_with_clamav(str(file_path))
    except ValueError as exc:
        storage_service.delete(str(file_path))
        messages = {
            "file_signature_mismatch": "File content does not match its extension",
            "invalid_office_file": "Invalid or damaged Office document",
            "malware_detected": "Malware was detected in the uploaded file",
            "virus_scanner_unavailable": "File security scanner is unavailable",
        }
        return ApiResponse(code=400, msg=messages.get(str(exc), "File security validation failed"))
    file_type = ext.lstrip(".")
    if file_type in ("jpg", "jpeg", "png", "bmp", "tiff"):
        file_type = "image"

    if visibility not in {"public", "internal", "confidential"}:
        return ApiResponse(code=400, msg="无效的可见范围")
    if chunk_template not in {"general", "sentence", "table", "qa"}:
        return ApiResponse(code=400, msg="无效的切分模板")
    db_user = (await db.execute(
        select(User).where(User.username == user["username"])
    )).scalar_one_or_none()
    if not db_user:
        return ApiResponse(code=401, msg="用户不存在")
    dept = None
    if department_id:
        try:
            dept = (await db.execute(
                select(Department).where(Department.id == uuid.UUID(department_id))
            )).scalar_one_or_none()
        except ValueError:
            return ApiResponse(code=400, msg="无效的部门ID")

    kb = None
    if knowledge_base_id:
        try:
            kb = (await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == uuid.UUID(knowledge_base_id))
            )).scalar_one_or_none()
        except ValueError:
            return ApiResponse(code=400, msg="无效的知识库ID")
    else:
        kb = (await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.name == "默认知识库")
        )).scalar_one_or_none()
    if not kb:
        return ApiResponse(code=404, msg="知识库不存在")
    # 创建文档记录
    doc = Document(
        title=filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=str(file_path),
        status="pending",
        uploader_id=db_user.id,
        visibility=visibility,
        knowledge_base_id=kb.id,
        chunk_template=chunk_template,
    )

    if dept:
        doc.department_id = dept.id

    db.add(doc)
    await db.flush()
    logger.info(f"Document uploaded: {filename} ({file_size} bytes)")

    await db.commit()
    try:
        task = parse_document.delay(str(doc.id))
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = f"索引任务提交失败: {str(exc)[:300]}"
        await db.commit()
        return ApiResponse(code=503, msg="文件已保存，但后台索引任务提交失败", data={"id": str(doc.id), "status": doc.status})

    return ApiResponse(
        msg="上传成功，正在后台解析和建立索引",
        data={
            "id": str(doc.id),
            "title": doc.title,
            "status": doc.status,
            "file_size": file_size,
            "chunks": 0,
            "task_id": task.id,
            "quality_report": doc.quality_report or {},
        },
    )


@router.get("/list", response_model=ApiResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    knowledge_base_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """文档列表"""
    db_user = (await db.execute(
        select(User).where(User.username == user["username"])
    )).scalar_one_or_none()
    if not db_user:
        return ApiResponse(code=401, msg="用户不存在")

    filters = []
    if user.get("role") != "admin":
        dept_id = select(Department.id).where(Department.name == db_user.department).scalar_subquery()
        filters.append(or_(
            Document.visibility.in_(["public", "internal"]),
            Document.uploader_id == db_user.id,
            Document.department_id == dept_id,
        ))
    if knowledge_base_id:
        try:
            filters.append(Document.knowledge_base_id == uuid.UUID(knowledge_base_id))
        except ValueError:
            return ApiResponse(code=400, msg="无效的知识库ID")

    stmt = (
        select(Document, KnowledgeBase.name)
        .outerjoin(KnowledgeBase, KnowledgeBase.id == Document.knowledge_base_id)
        .where(*filters)
        .order_by(Document.created_at.desc())
    )
    total_stmt = select(func.count(Document.id)).where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    docs = result.all()

    return ApiResponse(
        data={
            "items": [
                DocumentInfo(
                    id=str(d.id),
                    title=d.title,
                    file_type=d.file_type,
                    file_size=d.file_size,
                    status=d.status,
                    visibility=d.visibility,
                    page_count=d.page_count,
                    knowledge_base_id=str(d.knowledge_base_id) if d.knowledge_base_id else "",
                    knowledge_base_name=kb_name or "",
                    chunk_template=d.chunk_template,
                    error_message=d.error_message,
                    quality_report=d.quality_report or {},
                    created_at=str(d.created_at),
                    updated_at=str(d.updated_at),
                )
                for d, kb_name in docs
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )



async def _accessible_document(doc_id: uuid.UUID, user: dict, db: AsyncSession):
    db_user = (await db.execute(
        select(User).where(User.username == user["username"])
    )).scalar_one_or_none()
    if not db_user:
        return None
    stmt = select(Document).where(Document.id == doc_id)
    if user.get("role") != "admin":
        dept_id = select(Department.id).where(Department.name == db_user.department).scalar_subquery()
        stmt = stmt.where(or_(
            Document.visibility.in_(["public", "internal"]),
            Document.uploader_id == db_user.id,
            Document.department_id == dept_id,
        ))
    return (await db.execute(stmt)).scalar_one_or_none()


@router.get("/{doc_id}/chunks", response_model=ApiResponse)
async def get_document_chunks(
    doc_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid = uuid.UUID(doc_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的文档ID")
    doc = await _accessible_document(doc_uuid, user, db)
    if not doc:
        return ApiResponse(code=404, msg="文档不存在或无权访问")
    total = (await db.execute(
        select(func.count(DocumentChunk.id)).where(DocumentChunk.document_id == doc_uuid)
    )).scalar_one()
    chunks = (await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_uuid)
        .order_by(DocumentChunk.chunk_index)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )).scalars().all()
    return ApiResponse(data={
        "document": {
            "id": str(doc.id),
            "title": doc.title,
            "chunk_template": doc.chunk_template,
            "page_count": doc.page_count,
            "quality_report": doc.quality_report or {},
        },
        "items": [{
            "id": str(chunk.id),
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
            "content_type": chunk.content_type,
            "metadata": chunk.chunk_meta,
            "token_count": chunk.token_count,
            "has_embedding": chunk.embedding is not None,
            "has_multimodal_embedding": chunk.multimodal_embedding is not None,
        } for chunk in chunks],
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@router.post("/{doc_id}/reindex", response_model=ApiResponse)
async def reindex_document(
    doc_id: str,
    chunk_template: str = Query("general"),
    user: dict = Depends(require_permission("documents.write")),
    db: AsyncSession = Depends(get_db),
):
    if chunk_template not in {"general", "sentence", "table", "qa"}:
        return ApiResponse(code=400, msg="无效的切分模板")
    try:
        doc_uuid = uuid.UUID(doc_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的文档ID")
    doc = await _accessible_document(doc_uuid, user, db)
    db_user = (await db.execute(select(User).where(User.username == user["username"]))).scalar_one_or_none()
    if not doc or not db_user or (user.get("role") != "admin" and doc.uploader_id != db_user.id):
        return ApiResponse(code=404, msg="文档不存在或无权重新索引")
    doc.chunk_template = chunk_template
    doc.status = "pending"
    doc.error_message = ""
    await db.commit()
    try:
        task = parse_document.delay(str(doc.id))
        return ApiResponse(msg="已提交后台重新索引", data={"task_id": task.id, "status": "pending"})
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = f"索引任务提交失败: {str(exc)[:300]}"
        await db.commit()
        return ApiResponse(code=503, msg=doc.error_message)


@router.get("/{doc_id}/chunks/{chunk_id}/image")
async def get_chunk_image(
    doc_id: str,
    chunk_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid, chunk_uuid = uuid.UUID(doc_id), uuid.UUID(chunk_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的文档或分块ID")
    doc = await _accessible_document(doc_uuid, user, db)
    if not doc:
        return ApiResponse(code=404, msg="文档不存在或无权访问")
    chunk = (await db.execute(select(DocumentChunk).where(
        DocumentChunk.id == chunk_uuid, DocumentChunk.document_id == doc_uuid
    ))).scalar_one_or_none()
    if not chunk or not chunk.image_path or not Path(chunk.image_path).exists():
        return ApiResponse(code=404, msg="该引用没有可预览图片")
    return FileResponse(chunk.image_path)

@router.get("/{doc_id}/content")
async def get_document_content(
    doc_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        doc_uuid = uuid.UUID(doc_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的文档ID")
    doc = await _accessible_document(doc_uuid, user, db)
    if not doc or not doc.storage_path or not Path(doc.storage_path).exists():
        return ApiResponse(code=404, msg="原文不存在或无权访问")
    return FileResponse(
        path=doc.storage_path,
        filename=doc.title,
    )
@router.delete("/{doc_id}", response_model=ApiResponse)
async def delete_document(
    doc_id: str,
    user: dict = Depends(require_permission("documents.delete")),
    db: AsyncSession = Depends(get_db),
):
    """删除文档"""
    try:
        doc_uuid = uuid.UUID(doc_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的文档ID")

    stmt = select(Document).where(Document.id == doc_uuid)
    if user.get("role") != "admin":
        stmt = stmt.where(
            Document.uploader_id == select(User.id).where(User.username == user["username"]).scalar_subquery()
        )
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()

    if not doc:
        return ApiResponse(code=404, msg="文档不存在")

    # 删除文件
    if doc.storage_path:
        try:
            storage_service.delete(doc.storage_path)
        except Exception as e:
            logger.warning(f"Delete file failed: {e}")

    await db.delete(doc)
    logger.info(f"Document deleted: {doc.title}")
    return ApiResponse(msg="删除成功")
