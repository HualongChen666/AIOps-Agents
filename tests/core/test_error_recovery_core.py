# -*- coding: utf-8 -*-
"""Targeted tests for core.error_recovery.core helpers."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.error_recovery.core import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
    ErrorRecoveryManager,
    RetryConfig,
    RetryPolicy,
    retry_decorator,
    retry_with_policy,
    setup_error_recovery,
)


class TestCircuitBreakerConfig:
    def test_default_config(self) -> None:
        config = CircuitBreakerConfig()
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.expected_exception is Exception

    def test_custom_config(self) -> None:
        config = CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0, expected_exception=ValueError
        )
        assert config.failure_threshold == 2
        assert config.recovery_timeout == 0
        assert config.expected_exception is ValueError


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_successful_call(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig())
        result = await breaker.call(AsyncMock(return_value="ok"))
        assert result == "ok"
        assert breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_failure_counts_and_opens(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2))
        with pytest.raises(ValueError):
            await breaker.call(MagicMock(side_effect=ValueError("boom")))
        assert breaker.failure_count == 1
        with pytest.raises(ValueError):
            await breaker.call(MagicMock(side_effect=ValueError("boom")))
        assert breaker.get_state() == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_open_circuit_raises(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig())
        breaker.state = CircuitState.OPEN
        breaker.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=1)
        with pytest.raises(CircuitBreakerOpenError):
            await breaker.call(AsyncMock(return_value="ok"))

    @pytest.mark.asyncio
    async def test_half_open_recovery(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0))
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 2
        breaker.last_failure_time = datetime.now(timezone.utc)
        result = await breaker.call(AsyncMock(return_value="ok"))
        assert result == "ok"
        assert breaker.get_state() == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_half_open_failure_reopens(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0))
        breaker.state = CircuitState.OPEN
        breaker.failure_count = 2
        breaker.last_failure_time = datetime.now(timezone.utc)
        with pytest.raises(ValueError):
            await breaker.call(MagicMock(side_effect=ValueError("boom")))
        assert breaker.get_state() == CircuitState.OPEN

    def test_should_attempt_reset_without_last_failure(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=10))
        assert breaker._should_attempt_reset() is True

    def test_should_attempt_reset_after_timeout(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=1))
        breaker.last_failure_time = datetime.now(timezone.utc) - timedelta(seconds=2)
        assert breaker._should_attempt_reset() is True

    def test_should_not_attempt_reset_before_timeout(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig(recovery_timeout=60))
        breaker.last_failure_time = datetime.now(timezone.utc)
        assert breaker._should_attempt_reset() is False

    def test_get_stats(self) -> None:
        breaker = CircuitBreaker(CircuitBreakerConfig())
        stats = breaker.get_stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0


class TestRetry:
    def test_retry_config(self) -> None:
        config = RetryConfig(max_attempts=5, base_delay=0.1, max_delay=1.0, jitter=False)
        assert config.max_attempts == 5

    def test_retry_policy_should_retry(self) -> None:
        config = RetryConfig(
            max_attempts=3,
            retryable_exceptions=[ValueError],
        )
        policy = RetryPolicy(config)
        assert policy.should_retry(ValueError("x"), 1) is True
        assert policy.should_retry(TypeError("x"), 1) is False
        assert policy.should_retry(ValueError("x"), 3) is False

    def test_calculate_delay(self) -> None:
        config = RetryConfig(base_delay=1.0, max_delay=10.0, exponential_base=2.0, jitter=False)
        policy = RetryPolicy(config)
        assert policy.calculate_delay(1) == pytest.approx(1.0)
        assert policy.calculate_delay(2) == pytest.approx(2.0)
        assert policy.calculate_delay(5) == pytest.approx(10.0)

    @pytest.mark.asyncio
    async def test_retry_with_policy_success(self) -> None:
        config = RetryConfig(max_attempts=3, base_delay=0.0, jitter=False)
        func = AsyncMock(return_value="ok")
        with patch("core.error_recovery.core.asyncio.sleep", new_callable=AsyncMock):
            result = await retry_with_policy(func, config)
        assert result == "ok"
        func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_with_policy_failure(self) -> None:
        config = RetryConfig(
            max_attempts=2,
            base_delay=0.0,
            jitter=False,
            retryable_exceptions=[ValueError],
        )
        func = AsyncMock(side_effect=ValueError("boom"))
        with patch("core.error_recovery.core.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ValueError):
                await retry_with_policy(func, config)
        assert func.await_count == 2

    @pytest.mark.asyncio
    async def test_retry_decorator(self) -> None:
        config = RetryConfig(max_attempts=2, base_delay=0.0, jitter=False)

        @retry_decorator(config)
        async def func(x: int) -> int:
            return x + 1

        with patch("core.error_recovery.core.asyncio.sleep", new_callable=AsyncMock):
            assert await func(1) == 2


class TestErrorRecoveryManager:
    @pytest.mark.asyncio
    async def test_execute_without_circuit_breaker(self) -> None:
        manager = ErrorRecoveryManager()
        result = await manager.execute_with_circuit_breaker("missing", AsyncMock(return_value="ok"))
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker(self) -> None:
        manager = ErrorRecoveryManager()
        manager.register_circuit_breaker("test", CircuitBreakerConfig())
        result = await manager.execute_with_circuit_breaker("test", AsyncMock(return_value="ok"))
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_attempt_recovery_success(self) -> None:
        manager = ErrorRecoveryManager()
        manager.register_recovery_strategy("ValueError", AsyncMock(return_value=True))
        assert await manager.attempt_recovery(ValueError("x")) is True

    @pytest.mark.asyncio
    async def test_attempt_recovery_failure(self) -> None:
        manager = ErrorRecoveryManager()
        manager.register_recovery_strategy("ValueError", AsyncMock(side_effect=RuntimeError("x")))
        assert await manager.attempt_recovery(ValueError("x")) is False

    @pytest.mark.asyncio
    async def test_attempt_recovery_no_strategy(self) -> None:
        manager = ErrorRecoveryManager()
        assert await manager.attempt_recovery(ValueError("x")) is False

    def test_get_circuit_breaker_stats(self) -> None:
        manager = ErrorRecoveryManager()
        assert manager.get_circuit_breaker_stats("missing") is None
        manager.register_circuit_breaker("db", CircuitBreakerConfig())
        stats = manager.get_circuit_breaker_stats("db")
        assert stats["state"] == "closed"


class TestSetupErrorRecovery:
    @pytest.mark.asyncio
    async def test_setup_error_recovery(self) -> None:
        result = await setup_error_recovery()
        assert result["status"] == "success"
        assert "database" in result["circuit_breakers"]

    @pytest.mark.asyncio
    async def test_database_recovery(self) -> None:
        result = await setup_error_recovery()
        manager = ErrorRecoveryManager()
        manager._recovery_strategies = result.get("recovery_strategies", {})
        manager._recovery_strategies = {"DatabaseError": lambda e: True}  # type: ignore[assignment]
        assert await manager.attempt_recovery(ValueError("x")) is False
        manager._recovery_strategies = {
            "ValueError": AsyncMock(return_value=True)  # type: ignore[dict-item]
        }
        assert await manager.attempt_recovery(ValueError("x")) is True

    @pytest.mark.asyncio
    async def test_real_database_recovery(self) -> None:
        await setup_error_recovery()
        cm, session = MagicMock(), MagicMock()
        cm.__aenter__ = AsyncMock(return_value=session)
        cm.__aexit__ = AsyncMock(return_value=None)
        with patch("core.db_engine.AsyncSessionLocal", return_value=cm):
            assert (
                await ErrorRecoveryManager().attempt_recovery(ValueError("DatabaseError")) is False
            )
