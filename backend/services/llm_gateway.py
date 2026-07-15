"""
大模型网关
主模型：DeepSeek V4（deepseek-chat）
备用：DashScope 通义千问（qwen-vl-plus 等多模态）
多模态（看图）：DashScope qwen-vl-plus
"""
import json
from typing import AsyncGenerator, Optional

import httpx
from openai import AsyncOpenAI

from backend.config import settings
from backend.utils.logger import logger
from backend.services.circuit_breaker import AsyncCircuitBreaker


class ProviderUnavailableError(RuntimeError):
    pass


class LLMGateway:
    """大模型调用网关"""

    def __init__(self):
        self.timeout = httpx.Timeout(settings.PROVIDER_TIMEOUT_SECONDS, connect=min(10.0, settings.PROVIDER_TIMEOUT_SECONDS))
        self.breaker = AsyncCircuitBreaker(settings.PROVIDER_CIRCUIT_FAILURES, settings.PROVIDER_CIRCUIT_RECOVERY_SECONDS)
        self._deepseek_client: Optional[AsyncOpenAI] = None
        self._dashscope_client: Optional[AsyncOpenAI] = None

    # ===================== DeepSeek（主力模型）=====================

    @property
    def deepseek_client(self) -> AsyncOpenAI:
        """DeepSeek V4 客户端"""
        if self._deepseek_client is None:
            self._deepseek_client = AsyncOpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url="https://api.deepseek.com/v1",
                http_client=httpx.AsyncClient(timeout=self.timeout),
            )
        return self._deepseek_client

    # ===================== DashScope（多模态备用）=====================

    @property
    def dashscope_client(self) -> AsyncOpenAI:
        """DashScope（通义千问）客户端，用于多模态"""
        if self._dashscope_client is None:
            self._dashscope_client = AsyncOpenAI(
                api_key=settings.DASHSCOPE_API_KEY,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
                http_client=httpx.AsyncClient(timeout=self.timeout),
            )
        return self._dashscope_client

    # ===================== 路由解析 ======================

    def _resolve_client(self, model: str):
        """
        根据模型名选择合适的客户端
        - deepseek* → DeepSeek
        - qwen* → DashScope
        - 其他 → DeepSeek（默认主力）
        """
        if model.startswith("deepseek"):
            return self.deepseek_client, model
        elif model.startswith("qwen"):
            return self.dashscope_client, model
        else:
            # 默认走 DeepSeek
            return self.deepseek_client, model

    # ===================== 流式对话（主力）=====================

    async def stream_chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话（主用 DeepSeek V4，失败时自动切换 DashScope）
        """
        model = model or settings.LLM_MODEL
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        client, actual_model = self._resolve_client(model)
        tried_deepseek = "deepseek" in str(client.base_url).lower()

        try:
            stream = await self.breaker.call(lambda: client.chat.completions.create(
                model=actual_model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, stream=True,
            ))

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"LLM stream error ({model}): {e}")

            # 主模型失败 → failover
            if tried_deepseek:
                # DeepSeek 失败，尝试 DashScope
                logger.info("DeepSeek 失败，尝试 DashScope failover...")
                if settings.DASHSCOPE_API_KEY:
                    try:
                        stream = await self.dashscope_client.chat.completions.create(
                            model="qwen-plus",
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=True,
                        )
                        async for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                        return  # failover 成功
                    except Exception as e2:
                        logger.error(f"DashScope failover also failed: {e2}")
                else:
                    logger.warning("DashScope API Key 未配置，无法 failover")
            else:
                # DashScope 失败，尝试 DeepSeek
                logger.info("DashScope 失败，尝试 DeepSeek failover...")
                if settings.DEEPSEEK_API_KEY:
                    try:
                        stream = await self.deepseek_client.chat.completions.create(
                            model="deepseek-chat",
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            stream=True,
                        )
                        async for chunk in stream:
                            if chunk.choices and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                        return
                    except Exception as e2:
                        logger.error(f"DeepSeek failover also failed: {e2}")
                else:
                    logger.warning("DeepSeek API Key 未配置，无法 failover")

            # 所有尝试都失败了
            raise ProviderUnavailableError("AI_PROVIDER_UNAVAILABLE") from e

    # ===================== 非流式调用 ======================

    async def chat(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """非流式对话（主要用于内部调用）"""
        model = model or settings.LLM_MODEL
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_tokens = max_tokens or settings.LLM_MAX_TOKENS

        client, actual_model = self._resolve_client(model)

        try:
            response = await self.breaker.call(lambda: client.chat.completions.create(
                model=actual_model, messages=messages, temperature=temperature,
                max_tokens=max_tokens, stream=False,
            ))
            return response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM call error: {e}")
            raise ProviderUnavailableError("AI_PROVIDER_UNAVAILABLE") from e

    # ===================== 多模态 Vision（看图）======================

    async def stream_chat_with_images(
        self,
        messages: list[dict],
        images: list[str],  # base64 data URI 列表
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        多模态流式对话：文本 + 图片
        仅 DashScope/Qwen-VL 支持，DeepSeek 不支持多模态
        images: ["data:image/png;base64,..."]
        """
        model = model or "qwen-vl-plus"
        temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE
        max_tokens = max_tokens or 4096

        multimodal_messages = []
        for msg in messages:
            if msg["role"] == "user":
                content_parts = [{"type": "text", "text": msg["content"]}]
                for img_data in images:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": img_data},
                    })
                multimodal_messages.append({"role": "user", "content": content_parts})
            else:
                multimodal_messages.append(msg)

        try:
            stream = await self.dashscope_client.chat.completions.create(
                model=model,
                messages=multimodal_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Vision LLM error: {e}")
            raise ProviderUnavailableError("AI_PROVIDER_UNAVAILABLE") from e

    async def analyze_image(
        self,
        image_base64: str,
        prompt: str = "请描述这张图片的内容",
    ) -> str:
        """单张图片分析（使用 Qwen-VL）"""
        result = []
        async for token in self.stream_chat_with_images(
            messages=[{"role": "user", "content": prompt}],
            images=[image_base64],
            model="qwen-vl-plus",
        ):
            result.append(token)
        return "".join(result)


# 全局单例
llm_gateway = LLMGateway()
