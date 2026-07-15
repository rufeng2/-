"""User-scoped long-term semantic memory for preferences and task summaries."""
from __future__ import annotations

import re

from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import LongTermMemory, User
from backend.security.ai_guardrails import ai_guardrails
from backend.services.cache_service import cache_service
from backend.services.embedding_service import embedding_service
from backend.utils.logger import logger


class LongTermMemoryService:
    _preference = re.compile(r"(?:请记住|记住|以后请|我偏好|我习惯|我的部门是|我的岗位是)(.{2,180})")

    async def _user(self, username: str, db: AsyncSession) -> User | None:
        return (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()

    async def recall(self, username: str, query: str, db: AsyncSession) -> list[dict]:
        if not settings.LONG_TERM_MEMORY_ENABLED:
            return []
        user = await self._user(username, db)
        if not user:
            return []
        preferences = (await db.execute(
            select(LongTermMemory).where(
                LongTermMemory.user_id == user.id,
                LongTermMemory.kind == "preference",
            ).order_by(LongTermMemory.updated_at.desc()).limit(3)
        )).scalars().all()
        preference_items = [
            {"id": str(item.id), "kind": item.kind, "content": item.content, "metadata": item.memory_meta, "importance": item.importance, "score": 1.0}
            for item in preferences
        ]
        try:
            vector = await embedding_service.embed_text(query)
            if vector:
                rows = await db.execute(text("""
                    SELECT id, kind, content, metadata, importance,
                           1 - (embedding <=> CAST(:embedding AS vector)) AS score
                    FROM long_term_memories
                    WHERE user_id = :user_id AND embedding IS NOT NULL AND kind <> 'preference'
                    ORDER BY embedding <=> CAST(:embedding AS vector), importance DESC
                    LIMIT :limit
                """), {"embedding": str(vector), "user_id": user.id, "limit": settings.LONG_TERM_MEMORY_TOP_K})
                semantic_items = [
                    {"id": str(row[0]), "kind": row[1], "content": row[2], "metadata": row[3] or {}, "importance": row[4], "score": float(row[5] or 0)}
                    for row in rows if float(row[5] or 0) >= 0.35
                ]
                return preference_items + semantic_items
        except Exception as exc:
            logger.warning("Semantic memory recall failed, using recent memories: %s", exc)
        memories = (await db.execute(
            select(LongTermMemory).where(LongTermMemory.user_id == user.id)
            .order_by(LongTermMemory.importance.desc(), LongTermMemory.updated_at.desc())
            .limit(settings.LONG_TERM_MEMORY_TOP_K)
        )).scalars().all()
        recent_items = [{"id": str(item.id), "kind": item.kind, "content": item.content, "metadata": item.memory_meta, "importance": item.importance, "score": 0.0} for item in memories if item.kind != "preference"]
        return preference_items + recent_items

    async def remember_explicit_preference(self, username: str, query: str, db: AsyncSession) -> bool:
        match = self._preference.search(query)
        if not match:
            return False
        content = match.group(1).strip(" ，。.!！")
        if len(content) < 2 or ai_guardrails.contains_sensitive(content):
            return False
        return await self._store(username, "preference", content, {"source": "explicit"}, 90, db)

    async def remember_task(self, username: str, question: str, answer: str, domain: str, db: AsyncSession) -> bool:
        if not settings.LONG_TERM_MEMORY_ENABLED or len(answer) < 20:
            return False
        content = f"任务：{question[:220]}\n结论：{answer[:500]}"
        if ai_guardrails.contains_sensitive(content):
            return False
        return await self._store(username, "task_summary", content, {"domain": domain}, 50, db)

    async def _store(self, username: str, kind: str, content: str, metadata: dict, importance: int, db: AsyncSession) -> bool:
        user = await self._user(username, db)
        if not user:
            return False
        duplicate = (await db.execute(
            select(LongTermMemory.id).where(LongTermMemory.user_id == user.id, LongTermMemory.kind == kind, LongTermMemory.content == content)
        )).scalar_one_or_none()
        if duplicate:
            return False
        embedding = None if kind == "preference" else await embedding_service.embed_text(content)
        db.add(LongTermMemory(user_id=user.id, kind=kind, content=content, memory_meta=metadata, embedding=embedding, importance=importance))
        await db.flush()
        ids_to_delete = (await db.execute(
            select(LongTermMemory.id).where(LongTermMemory.user_id == user.id)
            .order_by(LongTermMemory.importance.desc(), LongTermMemory.updated_at.desc())
            .offset(settings.LONG_TERM_MEMORY_MAX_PER_USER)
        )).scalars().all()
        if ids_to_delete:
            await db.execute(delete(LongTermMemory).where(LongTermMemory.id.in_(ids_to_delete)))
        await cache_service.bump_version(f"memory:{username}")
        return True

    @staticmethod
    def build_context(memories: list[dict]) -> str:
        if not memories:
            return "（无相关长期记忆）"
        return "\n".join(f"- [{item['kind']}] {item['content']}" for item in memories)


long_term_memory_service = LongTermMemoryService()
