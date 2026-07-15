"""One-shot answer validation and retry planning."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re

from backend.config import settings
from backend.services.llm_gateway import llm_gateway
from backend.services.observability import REFLECTION_EVENTS
from backend.utils.logger import logger


_HIGH_RISK_QUERY = re.compile(r"(密码|密钥|凭据|身份证|银行卡|工资|薪酬|个人信息|机密|管理员|权限|删除|导出)", re.I)


def requires_buffered_validation(question: str, results: list[dict], has_images: bool) -> bool:
    if has_images or _HIGH_RISK_QUERY.search(question):
        return True
    scores = [float(item.get("rerank_score", item.get("score", 0.0)) or 0.0) for item in results]
    return not scores or max(scores) < 0.35


@dataclass(frozen=True)
class ReflectionResult:
    passed: bool
    reason: str
    retry_query: str = ""
    source: str = "heuristic"


class ReflectionService:
    async def validate(self, question: str, answer: str, context: str) -> ReflectionResult:
        if not answer.strip():
            REFLECTION_EVENTS.labels(outcome="retry_empty").inc()
            return ReflectionResult(False, "empty answer", question)
        if not context.strip() or "暂未找到相关" in context:
            passed = "未找到" in answer or "没有找到" in answer
            REFLECTION_EVENTS.labels(outcome="pass_no_context" if passed else "retry_no_context").inc()
            return ReflectionResult(passed, "no retrievable context", question if not passed else "")
        if not settings.REFLECTION_USE_LLM:
            passed = len(answer.strip()) >= 20
            REFLECTION_EVENTS.labels(outcome="pass_heuristic" if passed else "retry_short").inc()
            return ReflectionResult(passed, "heuristic length check", question if not passed else "")
        prompt = f"""Validate an enterprise RAG answer. Return JSON only:
{{"passed":true,"reason":"short reason","retry_query":"better retrieval query or empty"}}
Pass only when the answer directly addresses the question and its factual claims are supported by context. Do not require every sentence to have a citation.
Question: {question}
Context: {context[:7000]}
Answer: {answer[:3500]}"""
        try:
            raw = await llm_gateway.chat([{"role": "user", "content": prompt}], temperature=0.0, max_tokens=180)
            match = re.search(r"\{[\s\S]*\}", raw or "")
            payload = json.loads(match.group(0) if match else raw)
            passed = bool(payload.get("passed"))
            retry_query = str(payload.get("retry_query", "")).strip()[:500]
            REFLECTION_EVENTS.labels(outcome="pass" if passed else "retry").inc()
            return ReflectionResult(passed, str(payload.get("reason", ""))[:300], retry_query or question, "llm")
        except Exception as exc:
            logger.warning("Reflection validation failed open: %s", exc)
            REFLECTION_EVENTS.labels(outcome="validator_error").inc()
            return ReflectionResult(True, "validator unavailable; fail open", source="fallback")


reflection_service = ReflectionService()
