"""
对话 API: 聊天、会话管理、历史、反馈
"""
import uuid
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.session import get_db
from backend.db.models import Conversation, Message, User
from backend.schemas.chat import (
    ChatRequest, ChatResponse, ConversationInfo, MessageInfo, FeedbackRequest,
)
from backend.schemas.common import ApiResponse
from backend.utils.auth import get_current_user
from backend.core.rag_pipeline import rag_pipeline
from backend.services.query_rewriter import query_rewriter
from backend.utils.logger import logger
from backend.services.storage_service import storage_service
from backend.config import settings
from pathlib import Path

router = APIRouter(prefix="/api/chat", tags=["对话"])


@router.post("/image-upload", response_model=ApiResponse)
async def upload_chat_image(
    image: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """Store a temporary user image and return an opaque attachment id."""
    suffix = Path(image.filename or "image.png").suffix.lower()
    if suffix not in {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"}:
        return ApiResponse(code=400, msg="仅支持 JPG、PNG、BMP、TIFF 或 WebP 图片")
    content = await image.read()
    if len(content) > min(settings.MAX_UPLOAD_SIZE_MB, 10) * 1024 * 1024:
        return ApiResponse(code=413, msg="图片不能超过10MB")
    path = Path(storage_service.save(content, suffix, prefix="chat-"))
    return ApiResponse(msg="图片已上传", data={"image_id": path.name, "name": image.filename or path.name})


def _resolve_chat_images(image_ids: list[str]) -> list[str]:
    root = Path(settings.UPLOAD_DIR).resolve()
    resolved = []
    for image_id in image_ids[:3]:
        safe_name = Path(image_id).name
        if not safe_name.startswith("chat-"):
            continue
        candidate = (root / safe_name).resolve()
        if candidate.parent == root and candidate.exists():
            resolved.append(str(candidate))
    return resolved

@router.post("/send")
async def send_message(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """发送消息，流式返回"""
    question = req.question.strip()
    if not question:
        return StreamingResponse(
            _event_stream(json.dumps({"error": "请输入问题"}, ensure_ascii=False)),
            media_type="text/event-stream",
        )

    # 获取或创建会话
    conv_id = req.conversation_id
    if conv_id:
        try:
            conv_uuid = uuid.UUID(conv_id)
            stmt = select(Conversation).where(
                Conversation.id == conv_uuid,
                Conversation.user_id == select(User.id).where(User.username == user["username"]).scalar_subquery(),
            )
            result = await db.execute(stmt)
            conv = result.scalar_one_or_none()
            if not conv:
                conv_id = ""
        except (ValueError, TypeError):
            conv_id = ""

    if not conv_id:
        # 创建新会话
        user_result = await db.execute(
            select(User).where(User.username == user["username"])
        )
        db_user = user_result.scalar_one_or_none()
        conv = Conversation(
            user_id=db_user.id if db_user else None,
            title=question[:30] + ("..." if len(question) > 30 else ""),
        )
        db.add(conv)
        await db.flush()
        conv_id = str(conv.id)

    # 获取用户部门用于权限过滤
    user_department = ""
    if user.get("username"):
        user_result = await db.execute(
            select(User).where(User.username == user["username"])
        )
        db_user = user_result.scalar_one_or_none()
        if db_user:
            user_department = db_user.department

    # 流式响应
    async def generate():
        try:
            async for event in rag_pipeline.generate(
                query=question,
                conversation_id=conv_id,
                username=user["username"],
                user_department=user_department,
                db=db,
                knowledge_base_ids=req.knowledge_base_ids,
                user_image_paths=_resolve_chat_images(req.image_ids),
            ):
                yield event
        except Exception as e:
            logger.error(f"Chat error: {e}", exc_info=True)
            yield f"data: {json.dumps({'error': f'系统内部错误: {str(e)[:100]}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")



@router.post("/debug", response_model=ApiResponse)
async def debug_retrieval(
    req: ChatRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    db_user = (await db.execute(
        select(User).where(User.username == user["username"])
    )).scalar_one_or_none()
    if not db_user:
        return ApiResponse(code=401, msg="用户不存在")
    history = await rag_pipeline._get_history(req.conversation_id, db) if req.conversation_id else []
    rewritten_query = await query_rewriter.rewrite(req.question.strip(), history)
    results = await rag_pipeline.search(
        rewritten_query,
        db,
        db_user.department,
        top_k=10,
        knowledge_base_ids=req.knowledge_base_ids,
    )
    return ApiResponse(data={
        "query": req.question.strip(),
        "rewritten_query": rewritten_query,
        "knowledge_base_ids": req.knowledge_base_ids,
        "total": len(results),
        "items": [{
            "rank": index,
            "chunk_id": item.get("chunk_id"),
            "document_id": item.get("document_id"),
            "document_title": item.get("document_title"),
            "content_type": item.get("content_type"),
            "search_type": item.get("search_type"),
            "score": item.get("score"),
            "rrf_score": item.get("rrf_score"),
            "rerank_score": item.get("rerank_score"),
            "source_ranks": item.get("source_ranks", {}),
            "parent_id": item.get("parent_id", ""),
            "page": item.get("metadata", {}).get("page"),
            "snippet": item.get("content", "")[:500],
        } for index, item in enumerate(results, 1)],
    })
@router.get("/conversations", response_model=ApiResponse)
async def get_conversations(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取用户的会话列表"""
    user_result = await db.execute(
        select(User).where(User.username == user["username"])
    )
    db_user = user_result.scalar_one_or_none()
    if not db_user:
        return ApiResponse(code=404, msg="用户不存在")

    stmt = (
        select(Conversation)
        .where(Conversation.user_id == db_user.id)
        .order_by(Conversation.updated_at.desc())
        .limit(30)
    )
    result = await db.execute(stmt)
    convs = result.scalars().all()

    return ApiResponse(data=[
        ConversationInfo(
            id=str(c.id),
            title=c.title,
            created_at=str(c.created_at),
            updated_at=str(c.updated_at),
        )
        for c in convs
    ])


@router.delete("/conversations/{conv_id}", response_model=ApiResponse)
async def delete_conversation(
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除会话"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的会话ID")

    stmt = select(Conversation).where(
                Conversation.id == conv_uuid,
                Conversation.user_id == select(User.id).where(User.username == user["username"]).scalar_subquery(),
            )
    result = await db.execute(stmt)
    conv = result.scalar_one_or_none()

    if not conv:
        return ApiResponse(code=404, msg="会话不存在")

    await db.delete(conv)
    return ApiResponse(msg="删除成功")


@router.get("/history/{conv_id}", response_model=ApiResponse)
async def get_history(
    conv_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取会话的历史消息"""
    try:
        conv_uuid = uuid.UUID(conv_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的会话ID")

    stmt = (
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.conversation_id == conv_uuid,
            Conversation.user_id == select(User.id).where(User.username == user["username"]).scalar_subquery(),
        )
        .order_by(Message.created_at.asc())
    )
    result = await db.execute(stmt)
    msgs = result.scalars().all()

    return ApiResponse(data=[
        MessageInfo(
            id=str(m.id),
            role=m.role,
            content=m.content,
            references=m.references_json if isinstance(m.references_json, list) else [],
            feedback=m.feedback,
            created_at=str(m.created_at),
        )
        for m in msgs
    ])


@router.post("/feedback", response_model=ApiResponse)
async def submit_feedback(
    req: FeedbackRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """提交反馈"""
    try:
        msg_uuid = uuid.UUID(req.message_id)
    except (ValueError, TypeError):
        return ApiResponse(code=400, msg="无效的消息ID")

    stmt = (
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Message.id == msg_uuid,
            Conversation.user_id == select(User.id).where(User.username == user["username"]).scalar_subquery(),
        )
    )
    result = await db.execute(stmt)
    msg = result.scalar_one_or_none()

    if not msg:
        return ApiResponse(code=404, msg="消息不存在")

    msg.feedback = req.rating
    await db.flush()

    logger.info(f"Feedback: msg={req.message_id} rating={req.rating}")
    return ApiResponse(msg="反馈提交成功")


def _event_stream(data: str):
    """生成单个 SSE 事件"""
    yield f"data: {data}\n\n"
