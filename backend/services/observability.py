"""Stage-level latency and outcome metrics for the RAG workflow."""
from contextlib import contextmanager
import time

from prometheus_client import Counter, Histogram


RAG_STAGE_DURATION = Histogram(
    "rag_stage_duration_seconds",
    "Latency of individual RAG workflow stages",
    ["stage", "status"],
)
CACHE_EVENTS = Counter("rag_cache_events_total", "RAG cache outcomes", ["cache", "outcome"])
REFLECTION_EVENTS = Counter("rag_reflection_events_total", "RAG reflection outcomes", ["outcome"])
SAFETY_EVENTS = Counter("rag_safety_events_total", "RAG safety guard outcomes", ["stage", "outcome"])


class StageTimings:
    def __init__(self):
        self.started = time.perf_counter()
        self.values: dict[str, float] = {}

    @contextmanager
    def track(self, stage: str):
        started = time.perf_counter()
        status = "ok"
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.perf_counter() - started
            self.values[stage] = round(self.values.get(stage, 0.0) + elapsed, 4)
            RAG_STAGE_DURATION.labels(stage=stage, status=status).observe(elapsed)

    def finish(self) -> dict[str, float]:
        self.values["total"] = round(time.perf_counter() - self.started, 4)
        return dict(self.values)

    def record(self, stage: str, elapsed: float, status: str = "ok") -> None:
        self.values[stage] = round(self.values.get(stage, 0.0) + elapsed, 4)
        RAG_STAGE_DURATION.labels(stage=stage, status=status).observe(elapsed)
