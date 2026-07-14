"""Conversation-aware query rewriting for retrieval."""
import re

from backend.services.llm_gateway import llm_gateway
from backend.utils.logger import logger


class QueryRewriter:
    _context_markers = re.compile(
        r"(他|她|它|他们|这个|那个|上述|前面|刚才|其中|该|呢[？?]?$|还有|继续|详细说|什么意思)"
    )

    def should_rewrite(self, query: str, history: list[dict]) -> bool:
        if not history:
            return False
        compact = query.strip()
        return len(compact) < 18 or bool(self._context_markers.search(compact))

    async def rewrite(self, query: str, history: list[dict]) -> str:
        if not self.should_rewrite(query, history):
            return query
        transcript = "\n".join(
            f"{'用户' if item.get('role') == 'user' else '助手'}：{item.get('content', '')[:400]}"
            for item in history[-6:]
        )
        prompt = f"""你负责改写企业知识库检索问题。结合历史对话，把最新问题改写成一个语义完整、可独立检索的问题。
要求：
1. 补全代词、对象、时间和业务主题；
2. 不回答问题，不增加历史中不存在的事实；
3. 已经完整的问题保持原意；
4. 只输出改写后的单个问题，不要解释。

历史对话：
{transcript}

最新问题：{query}
"""
        try:
            rewritten = (await llm_gateway.chat(
                [{"role": "user", "content": prompt}], temperature=0.0, max_tokens=180
            )).strip().strip('"“”')
            if rewritten and 2 <= len(rewritten) <= 500:
                logger.info("Query rewritten: %s -> %s", query, rewritten)
                return rewritten
        except Exception as exc:
            logger.warning("Query rewrite failed: %s", exc)
        return query


query_rewriter = QueryRewriter()