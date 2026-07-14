"""Celery document parsing and indexing task."""
import asyncio
from uuid import UUID

from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.db.models import Document
from backend.db.session import AsyncSessionLocal, engine
from backend.services.indexing_service import index_document
from backend.utils.logger import logger


@celery_app.task(bind=True, max_retries=3, default_retry_delay=5, autoretry_for=())
def parse_document(self, doc_id: str):
    """Parse, clean, embed and atomically replace one document index."""
    logger.info("Index task started: %s", doc_id)
    final_attempt = self.request.retries >= self.max_retries

    async def execute():
        try:
            async with AsyncSessionLocal() as db:
                document = (await db.execute(select(Document).where(Document.id == UUID(doc_id)))).scalar_one_or_none()
                if not document:
                    raise ValueError("Document not found")
                document.status = "parsing"
                document.error_message = ""
                await db.commit()
            async with AsyncSessionLocal() as db:
                try:
                    count = await index_document(doc_id, db)
                    await db.commit()
                    return count
                except Exception as exc:
                    await db.rollback()
                    if final_attempt:
                        document = (await db.execute(select(Document).where(Document.id == UUID(doc_id)))).scalar_one_or_none()
                        if document:
                            document.status = "failed"
                            document.error_message = str(exc)[:1000]
                            await db.commit()
                    raise
        finally:
            await engine.dispose()

    try:
        count = asyncio.run(execute())
        logger.info("Index task complete: %s (%s chunks)", doc_id, count)
        return {"doc_id": doc_id, "status": "indexed", "chunks": count}
    except Exception as exc:
        logger.error("Index task failed: %s: %s", doc_id, exc, exc_info=True)
        if final_attempt:
            raise
        raise self.retry(exc=exc)