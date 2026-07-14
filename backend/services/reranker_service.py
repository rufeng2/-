"""Production reranking through DashScope, with optional local fallback."""
import asyncio
from typing import Optional

from dashscope import AioTextReRank

from backend.config import settings
from backend.utils.logger import logger

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    CrossEncoder = None


class RerankerService:
    def __init__(self):
        self._model = None
        self._model_name = settings.RERANKER_MODEL
        self._enabled = settings.RETRIEVAL_USE_RERANK
        self._provider = "dashscope" if settings.DASHSCOPE_API_KEY else "local"

    @property
    def is_ready(self) -> bool:
        return self._enabled and (bool(settings.DASHSCOPE_API_KEY) or CrossEncoder is not None)

    async def _dashscope_rerank(self, query: str, candidates: list[dict], k: int) -> list[dict]:
        documents = [
            f"{item.get('document_title', '')}\n{item.get('content', '')}".strip()
            for item in candidates
        ]
        response = await AioTextReRank.call(
            model=self._model_name,
            query=query,
            documents=documents,
            top_n=min(k, len(documents)),
            return_documents=False,
            api_key=settings.DASHSCOPE_API_KEY,
        )
        if getattr(response, "status_code", 200) != 200:
            raise RuntimeError(getattr(response, "message", "DashScope rerank failed"))
        output = getattr(response, "output", None)
        results = getattr(output, "results", None) or (output.get("results", []) if isinstance(output, dict) else [])
        ranked = []
        for result in results:
            index = getattr(result, "index", None)
            score = getattr(result, "relevance_score", None)
            if isinstance(result, dict):
                index = result.get("index", index)
                score = result.get("relevance_score", score)
            if index is None or not 0 <= int(index) < len(candidates):
                continue
            ranked.append({**candidates[int(index)], "rerank_score": float(score or 0), "score": float(score or 0)})
        return ranked

    def _ensure_local_model(self):
        if self._model is None and CrossEncoder is not None:
            self._model = CrossEncoder(self._model_name, max_length=512, device="cpu")

    async def _local_rerank(self, query: str, candidates: list[dict], k: int) -> list[dict]:
        self._ensure_local_model()
        if self._model is None:
            return candidates[:k]
        pairs = [(query, f"{item.get('document_title', '')}: {item.get('content', '')}") for item in candidates]
        scores = await asyncio.get_running_loop().run_in_executor(
            None, lambda: self._model.predict(pairs, show_progress_bar=False)
        )
        ranked = [{**item, "rerank_score": float(scores[i]), "score": float(scores[i])} for i, item in enumerate(candidates)]
        ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
        return ranked[:k]

    async def rerank(self, query: str, candidates: list[dict], top_k: Optional[int] = None) -> list[dict]:
        k = top_k or settings.RETRIEVAL_RERANK_TOP_K
        if not self._enabled or not candidates:
            return candidates[:k]
        try:
            if settings.DASHSCOPE_API_KEY:
                ranked = await self._dashscope_rerank(query, candidates, k)
                if ranked:
                    self._provider = "dashscope"
                    return ranked
            self._provider = "local"
            return await self._local_rerank(query, candidates, k)
        except Exception as exc:
            logger.error("Reranker failed, retaining RRF order: %s", exc)
            return candidates[:k]

    def get_model_info(self) -> dict:
        return {
            "model": self._model_name,
            "enabled": self._enabled,
            "ready": self.is_ready,
            "provider": self._provider,
        }


reranker = RerankerService()