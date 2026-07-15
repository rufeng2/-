"""Minimal async circuit breaker for external provider calls."""
from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar


T = TypeVar("T")


class CircuitOpenError(RuntimeError):
    pass


class AsyncCircuitBreaker:
    def __init__(self, failure_threshold: int = 3, recovery_seconds: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self.failures = 0
        self.state = "closed"
        self._opened_at = 0.0
        self._lock = asyncio.Lock()

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._lock:
            if self.state == "open":
                if time.monotonic() - self._opened_at < self.recovery_seconds:
                    raise CircuitOpenError("provider circuit is open")
                self.state = "half_open"
        try:
            result = await operation()
        except Exception:
            async with self._lock:
                self.failures += 1
                if self.failures >= self.failure_threshold:
                    self.state = "open"
                    self._opened_at = time.monotonic()
            raise
        async with self._lock:
            self.failures = 0
            self.state = "closed"
        return result
