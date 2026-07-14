"""Runnable composition for retrieval-augmented generation."""
from functools import lru_cache

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable

from backend.langchain_app.models import get_text_chat_model
from backend.langchain_app.prompts import RAG_PROMPT


def history_to_messages(history: list[dict]) -> list[BaseMessage]:
    messages: list[BaseMessage] = []
    for item in history:
        content = item.get("content", "")
        if item.get("role") == "assistant":
            messages.append(AIMessage(content=content))
        elif item.get("role") == "user":
            messages.append(HumanMessage(content=content))
    return messages


@lru_cache()
def get_rag_chain() -> Runnable:
    return RAG_PROMPT | get_text_chat_model() | StrOutputParser()

