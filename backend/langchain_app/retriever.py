"""Permission-aware LangChain retriever adapter."""
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.documents import Document as LangChainDocument
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field


class EnterpriseRetriever(BaseRetriever):
    """Expose the existing permission-filtered hybrid search as a Retriever."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    search_fn: Callable[[str], Awaitable[list[dict[str, Any]]]] = Field(exclude=True)

    async def _aget_relevant_documents(
        self,
        query: str,
        *,
        run_manager=None,
    ) -> list[LangChainDocument]:
        results = await self.search_fn(query)
        return [
            LangChainDocument(
                page_content=result.get("content", ""),
                metadata={
                    "chunk_id": result.get("chunk_id", ""),
                    "document_id": result.get("document_id", ""),
                    "document_title": result.get("document_title", "未知文档"),
                    "content_type": result.get("content_type", "text"),
                    "image_path": result.get("image_path", ""),
                    "score": result.get("score", 0.0),
                    "search_type": result.get("search_type", ""),
                    "chunk_metadata": result.get("metadata", {}),
                },
            )
            for result in results
        ]

    def _get_relevant_documents(self, query: str, *, run_manager=None):
        raise RuntimeError("EnterpriseRetriever only supports async retrieval")


def documents_to_results(documents: list[LangChainDocument]) -> list[dict]:
    """Convert LangChain documents back to the application's reference shape."""
    return [
        {
            "content": document.page_content,
            "metadata": document.metadata.get("chunk_metadata", {}),
            **{
                key: value
                for key, value in document.metadata.items()
                if key != "chunk_metadata"
            },
        }
        for document in documents
    ]

