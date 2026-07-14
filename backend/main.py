"""
多模态企业知识库 RAG 系统 - 主服务入口
FastAPI async + PostgreSQL pgvector + DashScope LLM
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from backend.config import settings
from backend.utils.logger import logger
from backend.api import auth, documents, chat, admin, knowledge_bases, evaluation, enterprise_auth, operations
from backend.services.llm_gateway import llm_gateway
from backend.services.reranker_service import reranker
from backend.db.session import AsyncSessionLocal
from backend.db.models import User
from backend.utils.auth import hash_password
from backend.db.migrations import ensure_runtime_schema
from backend.middleware.production import production_middleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("=" * 50)
    logger.info("📚 多模态企业知识库 RAG 系统启动")
    logger.info(f"环境: {settings.APP_ENV}")
    logger.info(f"LLM 模型: {settings.LLM_MODEL}")
    logger.info(f"嵌入维度: {settings.EMBEDDING_DIM}")
    logger.info("=" * 50)
    await ensure_runtime_schema()
    async with AsyncSessionLocal() as db:
        admin = (await db.execute(
            select(User).where(User.username == settings.ADMIN_USERNAME)
        )).scalar_one_or_none()
        if not admin:
            db.add(User(
                username=settings.ADMIN_USERNAME,
                password=hash_password(settings.ADMIN_PASSWORD),
                display_name="系统管理员",
                role="admin",
            ))
            await db.commit()
            logger.info("Administrator account initialized")
    yield
    logger.info("系统关闭")


app = FastAPI(
    title="企业知识库 RAG 系统",
    description="多模态企业知识库智能问答系统，支持文档上传、权限管理、RAG 对话",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS is explicit and environment-configurable.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.CORS_ORIGINS.split(",") if item.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def apply_production_middleware(request, call_next):
    return await production_middleware(request, call_next)


# Routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(admin.router)
app.include_router(knowledge_bases.router)
app.include_router(evaluation.router)
app.include_router(enterprise_auth.router)
app.include_router(operations.router)


@app.get("/api/health")
async def health():
    """健康检查 + 各模型状态"""
    return {
        "status": "ok",
        "app": "knowledge-rag",
        "models": {
            "chat": f"{settings.LLM_MODEL} (DeepSeek V4)",
            "orchestration": "LangChain Runnable",
            "embedding": "text-embedding-v3 + multimodal-embedding-v1 (unified)",
            "reranker": reranker.get_model_info(),
            "vision": "qwen-vl-plus (DashScope, 需 DASHSCOPE_API_KEY)" if settings.DASHSCOPE_API_KEY else "未配置",
        },
        "config": {
            "retrieval_top_k": settings.RETRIEVAL_TOP_K,
            "rerank_top_k": settings.RETRIEVAL_RERANK_TOP_K,
            "use_rerank": settings.RETRIEVAL_USE_RERANK,
        },
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": "企业知识库 RAG 系统",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "version": "1.0.0",
    }


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)