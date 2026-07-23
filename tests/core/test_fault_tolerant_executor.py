# -*- coding: utf-8 -*-
"""测试 L6 容错执行器"""

import asyncio

import pytest


class TestCircuitBreaker:
    def test_success_keeps_closed(self):
        from core.execution.l6.fault_tolerant_executor import CircuitBreaker, CircuitBreakerConfig

        cb = CircuitBreaker(CircuitBreakerConfig())
        result = asyncio.run(cb.call(lambda: "ok"))
        assert result == "ok"
        assert cb.get_state().value == "closed"

    def test_opens_after_failures(self):
        from core.execution.l6.fault_tolerant_executor import CircuitBreaker, CircuitBreakerConfig

        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            asyncio.run(cb.call(fail))
        assert cb.get_state().value == "open"

    def test_open_rejects_calls(self):
        from core.execution.l6.fault_tolerant_executor import (
            CircuitBreaker,
            CircuitBreakerConfig,
        )

        cb = CircuitBreaker(CircuitBreakerConfig(failure_threshold=1))

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            asyncio.run(cb.call(fail))
        with pytest.raises(Exception):
            asyncio.run(cb.call(lambda: "ok"))

    def test_half_open_reset(self):
        from core.execution.l6.fault_tolerant_executor import (
            CircuitBreaker,
            CircuitBreakerConfig,
        )

        cb = CircuitBreaker(
            CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0, half_open_max_calls=1)
        )

        def fail():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError):
            asyncio.run(cb.call(fail))
        asyncio.run(cb.call(lambda: "ok"))
        assert cb.get_state().value == "closed"


class TestFaultTolerantExecutor:
    def test_execute_success(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {
                "max_retries": 0,
                "base_delay": 0,
                "circuit_breaker_failure_threshold": 10,
            }
        )
        result = asyncio.run(executor.execute(lambda: "ok", "op"))
        assert result.status.value == "completed"
        assert result.result == "ok"

    def test_execute_retry_then_success(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {
                "max_retries": 2,
                "base_delay": 0,
                "exponential_backoff": False,
                "circuit_breaker_failure_threshold": 10,
            }
        )
        calls = []

        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise TimeoutError("boom")
            return "ok"

        result = asyncio.run(executor.execute(flaky, "op"))
        assert result.status.value == "completed"
        assert result.result == "ok"

    def test_execute_non_retryable_fails(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {
                "max_retries": 2,
                "base_delay": 0,
                "circuit_breaker_failure_threshold": 10,
            }
        )

        def fail():
            raise ValueError("nope")

        result = asyncio.run(executor.execute(fail, "op"))
        assert result.status.value == "failed"

    def test_execute_timeout_with_fallback(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {
                "default_timeout": 0.001,
                "circuit_breaker_failure_threshold": 10,
            }
        )
        executor.register_fallback("slow", lambda: "fallback")

        async def slow():
            await asyncio.sleep(10)

        result = asyncio.run(executor.execute(slow, "slow"))
        assert result.status.value == "completed"
        assert result.result == "fallback"

    def test_execute_failure_with_fallback(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {"max_retries": 0, "circuit_breaker_failure_threshold": 10}
        )
        executor.register_fallback("bad", lambda: "fallback")

        def fail():
            raise RuntimeError("boom")

        result = asyncio.run(executor.execute(fail, "bad"))
        assert result.status.value == "completed"
        assert result.result == "fallback"

    def test_circuit_breaker_opens(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {
                "max_retries": 0,
                "circuit_breaker_failure_threshold": 1,
            }
        )

        def fail():
            raise RuntimeError("boom")

        asyncio.run(executor.execute(fail, "op"))
        result = asyncio.run(executor.execute(lambda: "ok", "op"))
        assert result.status.value == "failed"

    def test_metrics(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor(
            {"max_retries": 0, "circuit_breaker_failure_threshold": 10}
        )
        asyncio.run(executor.execute(lambda: "ok", "op"))
        metrics = executor.get_metrics("op")
        assert metrics["total"] == 1
        assert metrics["success"] == 1

    def test_circuit_breaker_states_and_reset(self):
        from core.execution.l6.fault_tolerant_executor import FaultTolerantExecutor

        executor = FaultTolerantExecutor({"max_retries": 0, "circuit_breaker_failure_threshold": 1})

        def fail():
            raise RuntimeError("boom")

        asyncio.run(executor.execute(fail, "op"))
        states = executor.get_circuit_breaker_states()
        assert states["op"] == "open"

        assert executor.reset_circuit_breaker("op") is True
        assert executor.reset_circuit_breaker("missing") is False
        assert executor.get_circuit_breaker_states()["op"] == "closed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
