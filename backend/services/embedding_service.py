"""Text and unified multimodal embedding service."""
import base64
import hashlib
import math
import mimetypes
from pathlib import Path
from typing import Optional

import httpx
from dashscope import AioMultiModalEmbedding, MultiModalEmbeddingItemImage, MultiModalEmbeddingItemText
from openai import AsyncOpenAI

from backend.config import settings
from backend.utils.logger import logger


class EmbeddingService:
    def __init__(self):
        self.dim = settings.EMBEDDING_DIM
        self._client: Optional[AsyncOpenAI] = None
        self._last_multimodal_success = False

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                http_client=httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)),
            )
        return self._client

    def _local_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        normalized = " ".join(text.lower().split())
        tokens = normalized.split()
        tokens.extend(normalized[i:i + 2] for i in range(max(0, len(normalized) - 1)))
        for token in tokens:
            value = int.from_bytes(hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest(), "big")
            vector[value % self.dim] += 1.0 if value & 1 else -1.0
        norm = math.sqrt(sum(value * value for value in vector))
        return [value / norm for value in vector] if norm else vector

    async def embed_text(self, text: str) -> Optional[list[float]]:
        try:
            response = await self.client.embeddings.create(model="text-embedding-v3", input=text, dimensions=self.dim)
            return response.data[0].embedding
        except Exception as exc:
            logger.warning("Remote embedding failed, using local fallback: %s", exc)
            return self._local_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for start in range(0, len(texts), 25):
            batch = texts[start:start + 25]
            try:
                response = await self.client.embeddings.create(model="text-embedding-v3", input=batch, dimensions=self.dim)
                ordered = [None] * len(batch)
                for item in response.data:
                    ordered[item.index] = item.embedding
                all_embeddings.extend(ordered)
            except Exception as exc:
                logger.warning("Remote batch embedding failed, using local fallback: %s", exc)
                all_embeddings.extend(self._local_embedding(text) for text in batch)
        return all_embeddings

    @staticmethod
    def _image_data_uri(image_path: str) -> str:
        path = Path(image_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        payload = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{payload}"

    async def embed_multimodal(self, text: str, image_path: str = "") -> list[float]:
        """Place text, table OCR and image content in one retrieval vector space."""
        if not settings.DASHSCOPE_API_KEY:
            return await self.embed_text(text) or self._local_embedding(text)
        items = []
        if image_path and Path(image_path).exists():
            items.append(MultiModalEmbeddingItemImage(self._image_data_uri(image_path), factor=0.65))
            if text:
                items.append(MultiModalEmbeddingItemText(text[:4000], factor=0.35))
        else:
            items.append(MultiModalEmbeddingItemText(text[:6000], factor=1.0))
        try:
            response = await AioMultiModalEmbedding.call(
                model=settings.MULTIMODAL_EMBEDDING_MODEL,
                input=items,
                api_key=settings.DASHSCOPE_API_KEY,
                dimension=self.dim,
                output_type="dense",
                enable_fusion=True,
            )
            if getattr(response, "status_code", 200) != 200:
                raise RuntimeError(getattr(response, "message", "multimodal embedding failed"))
            output = response.output
            embeddings = output.get("embeddings", []) if isinstance(output, dict) else getattr(output, "embeddings", [])
            first = embeddings[0]
            vector = first.get("embedding") if isinstance(first, dict) else getattr(first, "embedding", None)
            if vector and len(vector) == self.dim:
                return list(vector)
            raise RuntimeError("multimodal embedding returned an invalid vector")
        except Exception as exc:
            logger.warning("Multimodal embedding failed, using text vector: %s", exc)
            return await self.embed_text(text) or self._local_embedding(text)

    async def embed_multimodal_batch(self, items: list[dict]) -> list[list[float]]:
        vectors = []
        for item in items:
            vectors.append(await self.embed_multimodal(item.get("content", ""), item.get("image_path", "")))
        return vectors

    async def embed_query(self, query: str) -> Optional[list[float]]:
        return await self.embed_text(query)

    async def embed_multimodal_query(self, query: str) -> list[float]:
        return await self.embed_multimodal(query)


embedding_service = EmbeddingService()