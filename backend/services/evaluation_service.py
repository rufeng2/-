"""Background RAG evaluation with label-based retrieval metrics."""
from __future__ import annotations

import json
import math
import re
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.core.rag_pipeline import rag_pipeline
from backend.db.models import EvaluationItem, EvaluationRun
from backend.services.llm_gateway import llm_gateway


async def judge_answer(question: str, answer: str, context: str, expected_answer: str) -> dict:
    if not answer:
        return {"faithfulness": 0.0, "answer_relevance": 0.0, "answer_correctness": None, "hallucination_rate": 1.0, "reason": "未生成答案"}
    prompt = f"""你是严格的企业知识库问答评测员。根据问题、检索上下文和人工标准答案评分。
分数范围0到1。faithfulness表示事实有上下文支持；answer_relevance表示直接回答问题；answer_correctness表示与人工答案一致。无人工答案时返回null。
只输出JSON：{{"faithfulness":0.0,"answer_relevance":0.0,"answer_correctness":null,"reason":"不超过80字"}}
问题：{question}\n检索上下文：{context[:7000]}\n人工答案：{expected_answer or '（未标注）'}\n模型答案：{answer[:3000]}"""
    try:
        raw = await llm_gateway.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=220)
        match = re.search(r"\{[\s\S]*\}", raw)
        payload = json.loads(match.group(0) if match else raw)
        def score(name):
            value = payload.get(name)
            return None if value is None else round(max(0.0, min(1.0, float(value))), 4)
        faithfulness = score("faithfulness") or 0.0
        return {
            "faithfulness": faithfulness,
            "answer_relevance": score("answer_relevance") or 0.0,
            "answer_correctness": score("answer_correctness"),
            "hallucination_rate": round(1.0 - faithfulness, 4),
            "reason": str(payload.get("reason", ""))[:300],
        }
    except Exception as exc:
        return {"faithfulness": 0.0, "answer_relevance": 0.0, "answer_correctness": None, "hallucination_rate": 1.0, "reason": f"裁判失败: {str(exc)[:120]}"}


def _is_relevant(item: EvaluationItem, result: dict) -> bool:
    """Return whether one retrieved chunk is relevant to the labelled question."""
    title = result.get("document_title", "")
    chunk_id = result.get("chunk_id", "")
    metadata = result.get("metadata") or {}
    page = metadata.get("page") or metadata.get("slide")

    if item.expected_chunk_ids:
        return chunk_id in item.expected_chunk_ids
    if item.expected_document_titles:
        return title in item.expected_document_titles
    if item.expected_pages:
        return page in item.expected_pages

    content = result.get("content", "").lower()
    keywords = [word.lower() for word in (item.expected_keywords or []) if word]
    return bool(keywords and any(word in content for word in keywords))


def _relevance_key(item: EvaluationItem, result: dict) -> str:
    """Deduplicate labelled retrieval units for recall and ranking metrics."""
    if not _is_relevant(item, result):
        return ""
    chunk_id = result.get("chunk_id", "")
    title = result.get("document_title", "")
    metadata = result.get("metadata") or {}
    page = metadata.get("page") or metadata.get("slide")
    if item.expected_chunk_ids:
        return f"chunk:{chunk_id}"
    if item.expected_document_titles:
        return f"document:{title}"
    if item.expected_pages:
        return f"page:{page}"
    return f"fallback:{chunk_id}"


def retrieval_metrics(
    item: EvaluationItem,
    results: list[dict],
    context_k: int | None = None,
) -> dict:
    """Calculate ranking metrics plus chunk-level precision for the LLM context."""
    ranked_results = results[:10]
    relevant_ranks, seen = [], set()
    for rank, result in enumerate(ranked_results, 1):
        key = _relevance_key(item, result)
        if key and key not in seen:
            seen.add(key)
            relevant_ranks.append(rank)

    has_labels = bool(item.expected_chunk_ids or item.expected_document_titles or item.expected_pages)
    expected_count = max(
        1,
        (
            len(item.expected_chunk_ids or [])
            or len(item.expected_document_titles or [])
            or len(item.expected_pages or [])
        ) if has_labels else len(relevant_ranks),
    )
    dcg = sum(1.0 / math.log2(rank + 1) for rank in relevant_ranks)
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(expected_count, 10) + 1))
    expected_titles = set(item.expected_document_titles or [])
    retrieved_titles = {result.get("document_title", "") for result in ranked_results}
    document_recall = (
        len(expected_titles & retrieved_titles) / len(expected_titles)
        if expected_titles
        else (1.0 if relevant_ranks else 0.0)
    )

    effective_context_k = max(1, context_k or settings.RETRIEVAL_RERANK_TOP_K)
    context_results = results[:effective_context_k]
    relevant_context_count = sum(1 for result in context_results if _is_relevant(item, result))
    return {
        "retrieval_hit": bool(relevant_ranks),
        "recall_at_5": 1.0 if any(rank <= 5 for rank in relevant_ranks) else 0.0,
        "recall_at_10": 1.0 if relevant_ranks else 0.0,
        "document_recall_at_10": document_recall,
        "reciprocal_rank": 1.0 / relevant_ranks[0] if relevant_ranks else 0.0,
        "ndcg_at_10": min(1.0, dcg / ideal) if ideal else 0.0,
        "context_precision": relevant_context_count / len(context_results) if context_results else 0.0,
        "context_relevant_count": relevant_context_count,
        "context_count": len(context_results),
        "relevant_ranks": relevant_ranks,
    }

async def evaluate_run(run_id: str, db: AsyncSession) -> dict:
    run = (await db.execute(select(EvaluationRun).where(EvaluationRun.id == UUID(run_id)))).scalar_one()
    options = run.options or {}
    limit = int(options.get("limit", 10))
    generate_answers = bool(options.get("generate_answers", False))
    run.status = "running"
    run.progress = 0
    await db.commit()
    label_count = (
        func.jsonb_array_length(EvaluationItem.expected_document_titles)
        + func.jsonb_array_length(EvaluationItem.expected_chunk_ids)
        + func.jsonb_array_length(EvaluationItem.expected_pages)
    )
    items = (await db.execute(
        select(EvaluationItem).where(EvaluationItem.enabled.is_(True))
        .order_by(label_count.desc(), EvaluationItem.created_at).limit(limit)
    )).scalars().all()
    details = []
    for index, item in enumerate(items, 1):
        kb_ids = [str(item.knowledge_base_id)] if item.knowledge_base_id else None
        results = await rag_pipeline.search(item.question, db, "", top_k=10, knowledge_base_ids=kb_ids)
        retrieval = retrieval_metrics(item, results, context_k=settings.RETRIEVAL_RERANK_TOP_K)
        context_results = results[:settings.RETRIEVAL_RERANK_TOP_K]
        context = "\n".join(result.get("content", "") for result in context_results)
        answer = ""
        if generate_answers and results:
            answer = await llm_gateway.chat([{"role": "user", "content": f"仅根据资料简洁回答。\n资料：{context[:6000]}\n问题：{item.question}"}], temperature=0.0, max_tokens=500)
        keywords = [word.lower() for word in (item.expected_keywords or []) if word]
        coverage = sum(1 for word in keywords if word in answer.lower()) / len(keywords) if keywords and answer else 0.0
        judge = await judge_answer(item.question, answer, context, item.expected_answer or "") if generate_answers else {
            "faithfulness": 0.0, "answer_relevance": 0.0, "answer_correctness": None, "hallucination_rate": 0.0, "reason": "本次未启用答案生成"
        }
        details.append({
            "item_id": str(item.id), "category": item.category, "question": item.question,
            "expected_answer": item.expected_answer or "", "expected_keywords": item.expected_keywords or [],
            "expected_document_titles": item.expected_document_titles or [], "answer": answer,
            **retrieval, "keyword_coverage": coverage,
            "faithfulness": judge["faithfulness"], "answer_relevance": judge["answer_relevance"],
            "answer_correctness": judge["answer_correctness"], "hallucination_rate": judge["hallucination_rate"],
            "judge_reason": judge["reason"], "top_documents": [result.get("document_title", "") for result in results],
        })
        run.progress = round(index * 100 / max(1, len(items)))
        run.sample_count = index
        run.details = list(details)
        await db.commit()
    count = len(details) or 1
    correctness = [item["answer_correctness"] for item in details if item["answer_correctness"] is not None]
    metrics = {
        "retrieval_hit_rate": sum(item["retrieval_hit"] for item in details) / count,
        "hit_rate": sum(item["retrieval_hit"] for item in details) / count,
        "recall_at_5": sum(item["recall_at_5"] for item in details) / count,
        "recall_at_10": sum(item["recall_at_10"] for item in details) / count,
        "document_recall_at_10": sum(item["document_recall_at_10"] for item in details) / count,
        "mrr": sum(item["reciprocal_rank"] for item in details) / count,
        "ndcg_at_10": sum(item["ndcg_at_10"] for item in details) / count,
        "context_precision": sum(item["context_precision"] for item in details) / count,
        "answer_keyword_coverage": sum(item["keyword_coverage"] for item in details) / count,
        "faithfulness": sum(item["faithfulness"] for item in details) / count if generate_answers else None,
        "answer_relevance": sum(item["answer_relevance"] for item in details) / count if generate_answers else None,
        "hallucination_rate": sum(item["hallucination_rate"] for item in details) / count if generate_answers else None,
        "answer_correctness": sum(correctness) / len(correctness) if correctness else None,
        "annotated_answer_count": sum(bool(item["expected_answer"]) for item in details),
        "judged_answer_count": len(correctness),
        "labelled_retrieval_count": sum(bool(item["expected_document_titles"]) for item in details),
        "context_top_k": settings.RETRIEVAL_RERANK_TOP_K,
    }
    run.metrics = metrics
    run.details = list(details)
    run.sample_count = len(details)
    run.progress = 100
    run.status = "completed"
    run.error_message = ""
    await db.commit()
    return metrics