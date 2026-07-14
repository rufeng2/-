"""LangChain chat model configuration with provider failover."""
from functools import lru_cache

from langchain_core.runnables import Runnable
from langchain_openai import ChatOpenAI

from backend.config import settings


@lru_cache()
def get_text_chat_model() -> Runnable:
    """Return DeepSeek with Qwen fallback using LangChain's fallback runnable."""
    primary = ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com/v1",
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        streaming=True,
        timeout=120,
        max_retries=1,
    )
    fallback = ChatOpenAI(
        model="qwen-plus",
        api_key=settings.DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        streaming=True,
        timeout=120,
        max_retries=1,
    )
    return primary.with_fallbacks([fallback])

