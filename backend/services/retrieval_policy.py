"""Explainable query complexity policy for adaptive retrieval depth."""
from dataclasses import dataclass
import re


@dataclass(frozen=True)
class RetrievalPlan:
    tier: str
    recall_k: int
    final_k: int


class RetrievalPolicy:
    """Choose retrieval depth without adding another model call."""

    _complex_markers = re.compile(
        r"(比较|对比|分析|原因|影响|优缺点|分别|综合|全部|多方面|为什么|如何|"
        r"流程|步骤|依据|以及|并且|同时|哪些方面|完整说明)"
    )
    _fact_markers = re.compile(
        r"^(谁|何时|什么时候|多少|是否|哪一个|什么是|.*是什么|.*是多少|.*有多少|.*何时|.*的定义)"
    )

    def plan(self, query: str, base_recall: int, base_final: int) -> RetrievalPlan:
        compact = "".join(query.split())
        complex_hits = len(self._complex_markers.findall(compact))

        if len(compact) >= 45 or complex_hits >= 2:
            return RetrievalPlan(
                tier="complex",
                recall_k=max(base_recall * 2, 40),
                final_k=max(base_final + 4, 10),
            )

        if len(compact) <= 18 and self._fact_markers.search(compact):
            return RetrievalPlan(
                tier="fact",
                recall_k=max(8, base_recall // 2),
                final_k=max(4, base_final - 2),
            )

        return RetrievalPlan(tier="standard", recall_k=base_recall, final_k=base_final)


retrieval_policy = RetrievalPolicy()
