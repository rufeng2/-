"""Celery task for long-running RAG evaluations."""
import asyncio
from uuid import UUID

from sqlalchemy import select

from backend.db.models import EvaluationRun
from backend.db.session import AsyncSessionLocal, engine
from backend.services.evaluation_service import evaluate_run
from backend.tasks.celery_app import celery_app
from backend.utils.logger import logger


@celery_app.task(bind=True)
def run_rag_evaluation(self, run_id: str):
    async def execute():
        try:
            async with AsyncSessionLocal() as db:
                return await evaluate_run(run_id, db)
        finally:
            await engine.dispose()
    try:
        metrics = asyncio.run(execute())
        return {"run_id": run_id, "status": "completed", "metrics": metrics}
    except Exception as exc:
        logger.error("Evaluation task failed: %s", exc, exc_info=True)
        message = str(exc)
        async def fail():
            try:
                async with AsyncSessionLocal() as db:
                    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == UUID(run_id)))).scalar_one_or_none()
                    if run:
                        run.status = "failed"
                        run.error_message = message[:1000]
                        await db.commit()
            finally:
                await engine.dispose()
        asyncio.run(fail())
        raise