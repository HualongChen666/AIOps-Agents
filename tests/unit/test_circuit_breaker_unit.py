# -*- coding: utf-8 -*-
# tests/unit/test_circuit_breaker_unit.py
# Circuit Breaker模块单元测试
import asyncio  # noqa: F401
from datetime import datetime, timedelta, timezone  # noqa: F401

import pytest  # noqa: F401


class TestCircuitState:
    """测试熔断器状态枚举"""

    def test_circuit_state_values(self):
        """测试熔断器状态枚举值"""
        from core.circuit_breaker import CircuitState

        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitBreakerError:
    """测试熔断器异常"""

    def test_circuit_breaker_error(self):
        """测试熔断器异常"""
        from core.circuit_breaker import CircuitBreakerError

        error = CircuitBreakerError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)


class TestCircuitBreaker:
    """测试熔断器"""

    def test_circuit_breaker_initialization(self):
        """测试熔断器初始化"""
        from core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60, timeout=30)

        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.timeout == 30
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_initialization_defaults(self):
        """测试熔断器初始化默认值"""
        from core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker()

        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout == 60
        assert breaker.state == CircuitState.CLOSED

    def test_circuit_breaker_record_success(self):
        """测试记录成功"""
        from core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=5)

        breaker.record_success()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 0

    def test_circuit_breaker_record_failure(self):
        """测试记录失败"""
        from core.circuit_breaker import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=5)

        # 记录4次失败，应该不会触发熔断
        for i in range(4):
            breaker.record_failure()

        assert breaker.state == CircuitState.CLOSED
        assert breaker._failure_count == 4

        # 记录第5次失败，应该触发熔断
        breaker.record_failure()

        assert breaker.state == CircuitState.OPEN
