"""Vector index maintenance tasks."""
import asyncio

from sqlalchemy import select

from backend.tasks.celery_app import celery_app
from backend.db.models import Document
from backend.db.session import AsyncSessionLocal
from backend.services.indexing_service import index_document
from backend.utils.logger import logger


@celery_app.task
def rebuild_vector_index():
    """Index all pending or failed documents."""
    async def run():
        indexed = 0
        failed = 0
        async with AsyncSessionLocal() as db:
            ids = (await db.execute(
                select(Document.id).where(Document.status.in_(["pending", "failed"]))
            )).scalars().all()
            for doc_id in ids:
                try:
                    await index_document(doc_id, db)
                    await db.commit()
                    indexed += 1
                except Exception:
                    await db.rollback()
                    failed += 1
        return {"indexed": indexed, "failed": failed}

    result = asyncio.run(run())
    logger.info(f"Vector index rebuild complete: {result}")
    return result
