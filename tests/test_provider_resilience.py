import unittest

from backend.services.circuit_breaker import AsyncCircuitBreaker, CircuitOpenError


class CircuitBreakerTests(unittest.IsolatedAsyncioTestCase):
    async def test_opens_after_failure_threshold(self):
        breaker = AsyncCircuitBreaker(failure_threshold=2, recovery_seconds=60)

        async def fail():
            raise TimeoutError("provider timeout")

        with self.assertRaises(TimeoutError):
            await breaker.call(fail)
        with self.assertRaises(TimeoutError):
            await breaker.call(fail)
        with self.assertRaises(CircuitOpenError):
            await breaker.call(fail)
        self.assertEqual(breaker.state, "open")

    async def test_success_resets_failure_count(self):
        breaker = AsyncCircuitBreaker(failure_threshold=2, recovery_seconds=0)

        async def fail():
            raise RuntimeError("failure")

        async def succeed():
            return "ok"

        with self.assertRaises(RuntimeError):
            await breaker.call(fail)
        self.assertEqual(await breaker.call(succeed), "ok")
        self.assertEqual(breaker.state, "closed")
        self.assertEqual(breaker.failures, 0)
