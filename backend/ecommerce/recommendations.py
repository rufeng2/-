from datetime import datetime, timezone

from backend.ecommerce.schemas import AgentAnalysis, RecommendedAction


class RecommendationStore:
    def __init__(self):
        self._items: dict[str, RecommendedAction] = {}

    def seed_from_analysis(self, analysis: AgentAnalysis) -> None:
        for item in analysis.recommendations:
            self._items.setdefault(item.id, item)

    def seed(self, items: list[RecommendedAction]) -> None:
        for item in items:
            self._items.setdefault(item.id, item)

    def list(self, status: str = "") -> list[RecommendedAction]:
        values = list(self._items.values())
        if status:
            values = [item for item in values if item.status == status]
        return sorted(values, key=lambda item: item.updated_at, reverse=True)

    def approve(self, recommendation_id: str, operator: str = "system") -> RecommendedAction:
        return self._transition(recommendation_id, "approved", operator)

    def reject(self, recommendation_id: str, operator: str = "system") -> RecommendedAction:
        return self._transition(recommendation_id, "rejected", operator)

    def _transition(self, recommendation_id: str, status: str, operator: str) -> RecommendedAction:
        if recommendation_id not in self._items:
            raise KeyError(recommendation_id)
        item = self._items[recommendation_id]
        if item.status != "pending":
            raise ValueError(f"Recommendation {recommendation_id} is already {item.status}")
        item.status = status
        item.operator = operator
        item.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
        return item
