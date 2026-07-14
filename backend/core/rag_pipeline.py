"""
RAG 全流程编排
查询分析 → 混合检索 → 权限过滤 → Prompt 组装 → LLM 生成
支持多模态：图片分析、流程图识别
"""
import json
from typing import AsyncGenerator, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.models import Document, DocumentChunk, Conversation, Message, User
from backend.services.llm_gateway import llm_gateway
from backend.services.embedding_service import embedding_service
from backend.services.reranker_service import reranker
from backend.services.query_rewriter import query_rewriter
from backend.services.storage_service import storage_service
from backend.utils.logger import logger
from backend.langchain_app.retriever import EnterpriseRetriever, documents_to_results
from backend.langchain_app.chains import get_rag_chain, history_to_messages

SYSTEM_PROMPT = """你是企业智能知识库助手"小知"，基于企业内部知识库为用户提供精准、专业的回答。

## 回答规范
1. **基于事实**：严格基于检索到的知识库内容回答，不要编造信息
2. **引用来源**：在相关句子后标注 [1][2]，不要生成“参考来源”清单，来源清单由系统统一展示
3. **信息不足时**：明确告知"知识库中未找到相关信息"，建议换种方式提问或联系相关部门
4. **结构清晰**：使用简短的段落、列表，避免长篇大论
5. **通俗易懂**：专业术语适当解释，让非专业背景的同事也能理解
6. **数据安全**：不要输出超出权限范围的信息，仅基于检索到的内容回答
7. **免责声明**：流程/制度类问题末尾提醒"具体以公司最新政策/合同条款为准"

## 多模态支持
- 如果用户上传了图片或问到了流程图/表格类问题，会同时提供 OCR 识别结果
- 分析图片中的文字、图表、流程时，结合 OCR 内容回答"""


class RAGPipeline:
    """RAG 检索生成全流程"""

    def __init__(self):
        self.top_k = settings.RETRIEVAL_TOP_K
        self.max_history = 6

    async def search(
        self,
        query: str,
        db: AsyncSession,
        user_department: str = "",
        top_k: Optional[int] = None,
        knowledge_base_ids: Optional[list[str]] = None,
        query_image_path: str = "",
    ) -> list[dict]:
        """Dense + lexical retrieval, standard RRF fusion, reranking and parent expansion."""
        final_k = top_k or settings.RETRIEVAL_RERANK_TOP_K
        recall_k = max(self.top_k, final_k)
        query_emb = await embedding_service.embed_multimodal(query, query_image_path) if query_image_path else await embedding_service.embed_multimodal_query(query)
        vector_results = await self._vector_search(query_emb, db, user_department, recall_k * 3, knowledge_base_ids) if query_emb else []
        keyword_results = await self._keyword_search(query, db, user_department, recall_k * 2, knowledge_base_ids)
        fused = self._rrf_fuse([vector_results, keyword_results], settings.RRF_K)
        reranked = await reranker.rerank(query, fused, min(len(fused), max(final_k * 4, final_k)))
        diversified = self._diversify_results(reranked, final_k)
        expanded = self._expand_parent_chunks(diversified)
        logger.info("Search query=%r vector=%s keyword=%s fused=%s reranked=%s", query, len(vector_results), len(keyword_results), len(fused), len(expanded))
        return expanded

    @staticmethod
    def _rrf_fuse(result_lists: list[list[dict]], rrf_k: int = 60) -> list[dict]:
        """Reciprocal Rank Fusion: score(d) = sum(1 / (k + rank))."""
        merged: dict[str, dict] = {}
        for results in result_lists:
            for rank, item in enumerate(results, 1):
                key = item.get("chunk_id")
                if not key:
                    continue
                if key not in merged:
                    merged[key] = {**item, "rrf_score": 0.0, "source_ranks": {}}
                source = item.get("search_type", "unknown")
                merged[key]["rrf_score"] += 1.0 / (rrf_k + rank)
                merged[key]["source_ranks"][source] = rank
        fused = list(merged.values())
        for item in fused:
            item["score"] = item["rrf_score"]
            item["search_type"] = "+".join(sorted(item["source_ranks"]))
        fused.sort(key=lambda item: item["rrf_score"], reverse=True)
        return fused

    @staticmethod
    def _diversify_results(results: list[dict], top_k: int, max_per_document: int = 2) -> list[dict]:
        """Keep high relevance while preventing one document from monopolizing context."""
        selected, deferred, counts = [], [], {}
        for item in results:
            document_id = item.get("document_id") or item.get("document_title") or "unknown"
            if counts.get(document_id, 0) < max_per_document:
                selected.append(item)
                counts[document_id] = counts.get(document_id, 0) + 1
            else:
                deferred.append(item)
            if len(selected) >= top_k:
                return selected
        for item in deferred:
            selected.append(item)
            if len(selected) >= top_k:
                break
        return selected
    @staticmethod
    def _expand_parent_chunks(results: list[dict]) -> list[dict]:
        """Use child chunks for matching and larger parent blocks for generation."""
        expanded = []
        for item in results:
            metadata = item.get("metadata") or {}
            expanded.append({**item, "matched_content": item.get("content", ""), "content": metadata.get("parent_content") or item.get("content", ""), "parent_id": metadata.get("parent_id", "")})
        return expanded
    async def _vector_search(self, query_emb, db, user_department, k, knowledge_base_ids=None, use_multimodal=True):
        vector_column = "dc.multimodal_embedding" if use_multimodal else "dc.embedding"
        perm_join = ""
        if user_department:
            perm_join = """
                AND (
                    d.visibility IN ('public', 'internal')
                    OR EXISTS (
                        SELECT 1 FROM chunk_permissions cp
                        WHERE cp.chunk_id = dc.id
                        AND cp.department_id IN (
                            SELECT id FROM departments WHERE name = :dept_name
                        )
                    )
                )
            """
        else:
            perm_join = "AND d.visibility IN ('public', 'internal')"

        kb_filter = "AND d.knowledge_base_id::text = ANY(CAST(:kb_ids AS text[]))" if knowledge_base_ids else ""
        sql = text(f"""
            SELECT
                dc.id, dc.content, dc.metadata, dc.document_id,
                COALESCE(d.title, '未知文档') AS doc_title,
                dc.content_type,
                dc.image_path,
                1 - ({vector_column} <=> CAST(:query_emb AS vector)) AS score
            FROM document_chunks dc
            LEFT JOIN documents d ON d.id = dc.document_id
            WHERE {vector_column} IS NOT NULL
            AND (d.status = 'indexed' OR d.status IS NULL)
            {perm_join}
            {kb_filter}
            ORDER BY {vector_column} <=> CAST(:query_emb AS vector)
            LIMIT :k
        """)
        params = {"query_emb": str(query_emb), "k": k}
        if user_department:
            params["dept_name"] = user_department
        if knowledge_base_ids:
            params["kb_ids"] = knowledge_base_ids

        try:
            rows = await db.execute(sql, params)
            return [
                {
                    "chunk_id": str(r[0]), "content": r[1], "metadata": r[2] or {},
                    "document_id": str(r[3]) if r[3] else "",
                    "document_title": r[4] or "",
                    "content_type": r[5] or "text",
                    "image_path": r[6] or "",
                    "score": float(r[7]) if r[7] else 0.0,
                    "search_type": "vector",
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def _keyword_search(self, query, db, user_department, k, knowledge_base_ids=None):
        query_ts = " & ".join(query.strip().split())
        if not query_ts:
            return []

        compact_query = "".join(query.strip().split())
        han_chars = "".join(char for char in compact_query if "\u4e00" <= char <= "\u9fff")
        patterns = [f"%{compact_query}%"]
        if len(han_chars) >= 2:
            patterns.extend(f"%{han_chars[i:i + 2]}%" for i in range(min(len(han_chars) - 1, 12)))

        perm_filter = ""
        if user_department:
            perm_filter = """
                AND (
                    d.visibility IN ('public', 'internal')
                    OR EXISTS (
                        SELECT 1 FROM chunk_permissions cp
                        WHERE cp.chunk_id = dc.id
                        AND cp.department_id IN (
                            SELECT id FROM departments WHERE name = :dept_name
                        )
                    )
                )
            """
        else:
            perm_filter = "AND d.visibility IN ('public', 'internal')"

        kb_filter = "AND d.knowledge_base_id::text = ANY(CAST(:kb_ids AS text[]))" if knowledge_base_ids else ""
        sql = text(f"""
            SELECT
                dc.id, dc.content, dc.metadata, dc.document_id,
                COALESCE(d.title, '未知文档') AS doc_title,
                dc.content_type, dc.image_path,
                GREATEST(
                    ts_rank(to_tsvector('simple', dc.content), plainto_tsquery('simple', :query)),
                    CASE WHEN dc.content ILIKE :like_query THEN 1.0 ELSE 0.2 END
                ) AS score
            FROM document_chunks dc
            LEFT JOIN documents d ON d.id = dc.document_id
            WHERE d.status = 'indexed'
            AND (
                to_tsvector('simple', dc.content) @@ plainto_tsquery('simple', :query)
                OR dc.content ILIKE ANY(CAST(:patterns AS text[]))
            )
            {perm_filter}
            {kb_filter}
            ORDER BY score DESC
            LIMIT :k
        """)
        params = {"query": query, "like_query": f"%{compact_query}%", "patterns": patterns, "k": k}
        if user_department:
            params["dept_name"] = user_department
        if knowledge_base_ids:
            params["kb_ids"] = knowledge_base_ids

        try:
            rows = await db.execute(sql, params)
            return [
                {
                    "chunk_id": str(r[0]), "content": r[1], "metadata": r[2] or {},
                    "document_id": str(r[3]) if r[3] else "",
                    "document_title": r[4] or "",
                    "content_type": r[5] or "text",
                    "image_path": r[6] or "",
                    "score": float(r[7]) if r[7] else 0.0,
                    "search_type": "keyword",
                }
                for r in rows
            ]
        except Exception as e:
            logger.error(f"Keyword search error: {e}")
            return []

    def _build_context(self, results: list[dict]) -> str:
        if not results:
            return "（知识库中暂未找到相关文档）"

        parts = []
        for i, r in enumerate(results, 1):
            title = r.get("document_title", "未知文档")
            content = r.get("content", "")
            ctype = r.get("content_type", "text")
            type_tag = "🖼️ " if ctype == "image" else ""
            parts.append(f"[{i}] {type_tag}来自《{title}》\n{content}")
        return "\n\n---\n\n".join(parts)

    def _build_references(self, results: list[dict]) -> list[dict]:
        refs = []
        by_title = {}
        for r in results:
            title = r.get("document_title", "未知文档")
            if not title:
                continue
            metadata = r.get("metadata") or {}
            candidate = {
                "title": title,
                "document_id": r.get("document_id", ""),
                "chunk_id": r.get("chunk_id", ""),
                "page": metadata.get("page") or metadata.get("slide"),
                "content_type": r.get("content_type", "text"),
                "snippet": r.get("content", "")[:200],
                "bbox": metadata.get("bbox", []),
                "has_image": bool(r.get("image_path")),
            }
            if title not in by_title:
                by_title[title] = candidate
                refs.append(candidate)
            elif candidate["has_image"] and not by_title[title]["has_image"]:
                by_title[title].update(candidate)
        return refs[:5]

    async def _get_history(self, conversation_id: str, db: AsyncSession) -> list[dict]:
        try:
            conv_uuid = UUID(conversation_id)
        except (ValueError, TypeError):
            return []

        stmt = (
            select(Message)
            .where(Message.conversation_id == conv_uuid)
            .order_by(Message.created_at.asc())
            .limit(self.max_history * 2)
        )
        rows = await db.execute(stmt)
        msgs = rows.scalars().all()
        return [
            {"role": m.role, "content": m.content[:500]} for m in msgs
        ][-(self.max_history * 2):]

    async def _get_or_create_conv(
        self, conversation_id: str, username: str, db: AsyncSession
    ) -> tuple[str, bool]:
        """获取或创建会话，返回 (conv_id, is_new)"""
        try:
            conv_uuid = UUID(conversation_id)
            stmt = select(Conversation).where(Conversation.id == conv_uuid)
            result = await db.execute(stmt)
            conv = result.scalar_one_or_none()
            if conv:
                return str(conv.id), False
        except (ValueError, TypeError):
            pass

        # 创建新会话
        user_stmt = select(User).where(User.username == username)
        user_result = await db.execute(user_stmt)
        db_user = user_result.scalar_one_or_none()

        conv = Conversation(
            user_id=db_user.id if db_user else None,
            title="新对话",
        )
        db.add(conv)
        await db.flush()
        return str(conv.id), True

    async def _save_message(
        self, conv_id: str, role: str, content: str,
        references: list[dict], db: AsyncSession,
    ):
        """保存消息到数据库"""
        try:
            conv_uuid = UUID(conv_id)
            msg = Message(
                conversation_id=conv_uuid,
                role=role,
                content=content,
                references_json=references if role == "assistant" else [],
            )
            db.add(msg)
            await db.flush()
            return str(msg.id)
        except Exception as e:
            logger.error(f"Save message error: {e}")
            return ""

    async def generate(
        self,
        query: str,
        conversation_id: str,
        username: str,
        user_department: str,
        db: AsyncSession,
        knowledge_base_ids: Optional[list[str]] = None,
        user_image_paths: Optional[list[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        完整 RAG 流程
        Yields: SSE 格式事件
        """
        # ---- Step 1: 获取/创建会话 ----
        conv_id, is_new = await self._get_or_create_conv(conversation_id, username, db)
        if is_new:
            yield f"data: {json.dumps({'conv_created': True, 'conversation_id': conv_id}, ensure_ascii=False)}\n\n"

        # Rewrite only the retrieval query; keep the original question for the answer.
        prior_history = await self._get_history(conv_id, db)
        retrieval_query = await query_rewriter.rewrite(query, prior_history)
        if retrieval_query != query:
            yield f"data: {json.dumps({'rewritten_query': retrieval_query}, ensure_ascii=False)}\n\n"
        # 保存用户消息
        user_msg_id = await self._save_message(conv_id, "user", query, [], db)
        if user_msg_id:
            yield f"data: {json.dumps({'user_msg_id': user_msg_id}, ensure_ascii=False)}\n\n"

        # ---- Step 2: 检索 ----
        retriever = EnterpriseRetriever(
            search_fn=lambda question: self.search(
                question, db, user_department, knowledge_base_ids=knowledge_base_ids,
                query_image_path=(user_image_paths or [""])[0]
            )
        )
        documents = await retriever.ainvoke(retrieval_query)
        results = documents_to_results(documents)
        context = self._build_context(results)
        references = self._build_references(results)

        # ---- Step 3: 检查是否为图片/多模态问题 ----
        has_image_docs = any(r.get("content_type") == "image" for r in results) or bool(user_image_paths)
        image_paths = list(user_image_paths or []) + [
            r.get("image_path") for r in results
            if r.get("content_type") == "image" and r.get("image_path")
        ]
        image_paths = list(dict.fromkeys(path for path in image_paths if path))[:3]

        # ---- Step 4: 获取历史 ----
        history = await self._get_history(conv_id, db)
        if history and history[-1].get("role") == "user" and history[-1].get("content") == query:
            history = history[:-1]
        history_text = ""
        if history:
            for h in history:
                role_label = "用户" if h["role"] == "user" else "小知"
                history_text += f"{role_label}: {h['content']}\n"

        # ---- Step 5: 构建 Prompt ----
        user_prompt = f"""## 检索到的知识库内容
{context}

## 历史对话
{history_text if history_text else "（首次对话）"}

## 用户问题
{query}

请基于以上知识库内容回答："""

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        for h in history:
            messages.append(h)
        messages.append({"role": "user", "content": user_prompt})

        # ---- Step 6: 流式生成（多模态 or 纯文本） ----
        full_answer = ""
        msg_id = ""

        try:
            if has_image_docs and image_paths:
                # 多模态回答：尝试读取图片并发送给 Vision LLM
                import base64
                from pathlib import Path

                image_base64s = []
                for ip in image_paths[:2]:  # 最多带2张图
                    p = Path(ip)
                    if p.exists():
                        with open(p, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode()
                            mime = "image/png" if ip.lower().endswith(".png") else "image/jpeg"
                            image_base64s.append(f"data:{mime};base64,{b64}")

                if image_base64s:
                    async for token in llm_gateway.stream_chat_with_images(
                        messages=[{"role": "user", "content": user_prompt + "\n\n请同时分析附带的图片/图表内容。"}],
                        images=image_base64s,
                    ):
                        full_answer += token
                        yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
                else:
                    # 图片文件不可读，回退纯文本
                    async for token in llm_gateway.stream_chat(messages):
                        full_answer += token
                        yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
            else:
                chain = get_rag_chain()
                chain_input = {
                    "context": context,
                    "question": query,
                    "history": history_to_messages(history),
                }
                async for token in chain.astream(chain_input):
                    if token:
                        full_answer += token
                        yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

        except Exception as e:
            logger.error(f"Generation error: {e}", exc_info=True)
            fallback = f"抱歉，AI 服务暂时不可用。以下是检索到的相关文档：\n\n{context}\n\n如需进一步帮助，请联系技术支持。"
            yield f"data: {json.dumps({'token': fallback}, ensure_ascii=False)}\n\n"
            full_answer = fallback

        # ---- Step 7: 保存助手消息；来源清单由前端根据结构化 references 统一展示 ----

        msg_id = await self._save_message(conv_id, "assistant", full_answer, references, db)

        # ---- Step 9: 更新会话标题（首次对话）----
        if is_new:
            try:
                conv_uuid = UUID(conv_id)
                stmt = select(Conversation).where(Conversation.id == conv_uuid)
                result = await db.execute(stmt)
                conv = result.scalar_one_or_none()
                if conv:
                    conv.title = query[:30] + ("..." if len(query) > 30 else "")
            except Exception:
                pass

        # User chat attachments are one-shot inputs; remove local/MinIO copies after generation.
        for attachment_path in user_image_paths or []:
            try:
                storage_service.delete(attachment_path)
            except Exception as exc:
                logger.warning("Chat attachment cleanup failed: %s", exc)
        # ---- Step 10: 返回完成信号 ----
        payload = {
            'done': True,
            'conversation_id': conv_id,
            'message_id': msg_id,
            'references': references,
        }
        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


rag_pipeline = RAGPipeline()
