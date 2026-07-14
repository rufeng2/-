"""Offline smoke tests for the LangChain integration."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.langchain_app.chains import get_rag_chain, history_to_messages
from backend.langchain_app.retriever import EnterpriseRetriever, documents_to_results


async def fake_search(query: str) -> list[dict]:
    return [{
        "content": f"与 {query} 相关的企业知识",
        "chunk_id": "chunk-1",
        "document_id": "document-1",
        "document_title": "测试制度",
        "content_type": "text",
        "score": 0.9,
        "search_type": "hybrid",
    }]


async def main() -> None:
    retriever = EnterpriseRetriever(search_fn=fake_search)
    documents = await retriever.ainvoke("报销")
    results = documents_to_results(documents)

    assert documents[0].page_content
    assert results[0]["document_title"] == "测试制度"
    assert len(history_to_messages([
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好"},
    ])) == 2
    assert get_rag_chain() is not None
    print("OK: LangChain retriever, prompt, history and runnable")


if __name__ == "__main__":
    asyncio.run(main())

