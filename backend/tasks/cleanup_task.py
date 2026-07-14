"""Periodic data retention tasks."""
import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from backend.config import settings
from backend.db.models import AuditLog, Conversation
from backend.db.session import AsyncSessionLocal, engine
from backend.tasks.celery_app import celery_app
from backend.utils.logger import logger


@celery_app.task
def cleanup_expired_data():
    async def run():
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            conversations = await db.execute(
                delete(Conversation)
                .where(Conversation.updated_at < now - timedelta(days=max(settings.CONVERSATION_RETENTION_DAYS, 1)))
                .returning(Conversation.id)
            )
            audits = await db.execute(
                delete(AuditLog)
                .where(AuditLog.created_at < now - timedelta(days=max(settings.AUDIT_RETENTION_DAYS, 1)))
                .returning(AuditLog.id)
            )
            counts = {"conversations": len(conversations.scalars().all()), "audit_logs": len(audits.scalars().all())}
            await db.commit()
        await engine.dispose()
        return counts

    deleted = asyncio.run(run())
    logger.info(f"Retention cleanup completed: {deleted}")
    return deleted


@celery_app.task
def cleanup_expired_sessions(days: int = 30):
    """Backward-compatible task name."""
    return cleanup_expired_data.run()