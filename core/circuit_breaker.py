# -*- coding: utf-8 -*-
"""
Circuit Breaker Framework
熔断器框架，防止级联故障

功能:
- 熔断器状态管理（关闭/打开/半开）
- 失败率阈值检测
- 自动恢复机制
- 超时控制
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Dict, Optional, Type, Union  # noqa: F401

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """熔断器状态"""

    CLOSED = "closed"  # 关闭状态：正常工作
    OPEN = "open"  # 打开状态：熔断中
    HALF_OPEN = "half_open"  # 半开状态：尝试恢复


class CircuitBreakerError(Exception):
    """熔断器异常"""


class CircuitBreaker:
    """
    熔断器

    参数:
        failure_threshold: 失败阈值（次数）
        recovery_timeout: 恢复超时（秒）
        expected_exception: 预期的异常类型
        timeout: 单次调用超时（秒）
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[BaseException] = Exception,
        timeout: Optional[float] = None,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.timeout = timeout

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._success_count = 0
        self._call_count = 0

        logger.info(
            "Circuit breaker initialized: threshold=%d, timeout=%ds, call_timeout=%s",
            failure_threshold,
            recovery_timeout,
            timeout,
        )

    @property
    def state(self) -> CircuitState:
        """获取当前状态"""
        # 检查是否可以从OPEN恢复到HALF_OPEN
        if self._state == CircuitState.OPEN:
            if self._last_failure_time and (datetime.now() - self._last_failure_time) >= timedelta(
                seconds=self.recovery_timeout
            ):
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
                logger.info("Circuit breaker transitioned to HALF_OPEN")

        return self._state

    def record_success(self) -> None:
        """记录成功调用"""
        self._failure_count = 0
        self._success_count += 1

        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下连续成功则恢复到关闭状态
            if self._success_count >= 2:
                self._state = CircuitState.CLOSED
                logger.info("Circuit breaker recovered to CLOSED")

    def record_failure(self) -> None:
        """记录失败调用"""
        self._failure_count += 1
        self._last_failure_time = datetime.now()

        if self._state == CircuitState.HALF_OPEN:
            # 半开状态下失败则重新打开
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker re-opened from HALF_OPEN")
        elif self._failure_count >= self.failure_threshold:
            # 达到失败阈值，打开熔断器
            self._state = CircuitState.OPEN
            logger.warning("Circuit breaker opened after %d failures", self._failure_count)

    def allow_request(self) -> bool:
        """检查是否允许请求"""
        if self.state == CircuitState.OPEN:
            return False
        return True

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "call_count": self._call_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": (
                self._last_failure_time.isoformat() if self._last_failure_time else None
            ),
        }

    def reset(self) -> None:
        """重置熔断器"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._call_count = 0
        self._last_failure_time = None
        logger.info("Circuit breaker reset")


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type[BaseException] = Exception,
    timeout: Optional[float] = None,
):
    """
    熔断器装饰器

    参数:
        failure_threshold: 失败阈值
        recovery_timeout: 恢复超时（秒）
        expected_exception: 预期的异常类型
        timeout: 单次调用超时（秒）

    使用示例:
        @circuit_breaker(failure_threshold=3, recovery_timeout=30)
        async def external_api_call():
            # 调用外部API
            return response
    """
    breaker = CircuitBreaker(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        timeout=timeout,
    )

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            breaker._call_count += 1

            # 检查是否允许请求
            if not breaker.allow_request():
                raise CircuitBreakerError(
                    f"Circuit breaker is {breaker.state.value}, request rejected"
                )

            try:
                # 执行函数（带超时）
                if breaker.timeout:
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=breaker.timeout)
                else:
                    result = await func(*args, **kwargs)

                # 记录成功
                breaker.record_success()
                return result

            except asyncio.TimeoutError as e:
                breaker.record_failure()
                logger.error("Circuit breaker: timeout after %s seconds", breaker.timeout)
                raise CircuitBreakerError(f"Call timeout after {breaker.timeout}s") from e

            except expected_exception as e:
                breaker.record_failure()
                logger.error("Circuit breaker: expected exception %s: %s", type(e).__name__, e)
                raise

            except Exception as e:
                # 非预期异常也记录失败
                breaker.record_failure()
                logger.error("Circuit breaker: unexpected exception %s: %s", type(e).__name__, e)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            breaker._call_count += 1

            if not breaker.allow_request():
                raise CircuitBreakerError(
                    f"Circuit breaker is {breaker.state.value}, request rejected"
                )

            try:
                if breaker.timeout:
                    start_time = time.time()
                    result = func(*args, **kwargs)
                    elapsed = time.time() - start_time
                    if elapsed > breaker.timeout:
                        raise TimeoutError(f"Call timeout after {elapsed}s")
                else:
                    result = func(*args, **kwargs)

                breaker.record_success()
                return result

            except (TimeoutError, expected_exception) as e:
                breaker.record_failure()
                logger.error("Circuit breaker: exception %s: %s", type(e).__name__, e)
                raise

            except Exception as e:
                breaker.record_failure()
                logger.error("Circuit breaker: unexpected exception %s: %s", type(e).__name__, e)
                raise

        # 根据函数类型返回对应的wrapper
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class CircuitBreakerRegistry:
    """
    熔断器注册表

    管理多个熔断器实例
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def register(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[BaseException] = Exception,
        timeout: Optional[float] = None,
    ) -> CircuitBreaker:
        """
        注册熔断器

        参数:
            name: 熔断器名称
            failure_threshold: 失败阈值
            recovery_timeout: 恢复超时
            expected_exception: 预期异常
            timeout: 超时时间

        返回:
            熔断器实例
        """
        breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            timeout=timeout,
        )
        self._breakers[name] = breaker
        logger.info("Registered circuit breaker: %s", name)
        return breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """获取熔断器"""
        return self._breakers.get(name)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有熔断器的统计信息"""
        return {name: breaker.get_stats() for name, breaker in self._breakers.items()}

    def reset(self, name: str) -> bool:
        """重置熔断器"""
        if name in self._breakers:
            self._breakers[name].reset()
            return True
        return False

    def reset_all(self) -> None:
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()
        logger.info("All circuit breakers reset")


# 全局熔断器注册表
_global_registry = CircuitBreakerRegistry()


def get_circuit_breaker(name: str) -> Optional[CircuitBreaker]:
    """获取全局熔断器"""
    return _global_registry.get(name)


def register_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
    expected_exception: type[BaseException] = Exception,
    timeout: Optional[float] = None,
) -> CircuitBreaker:
    """注册全局熔断器"""
    return _global_registry.register(
        name=name,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        timeout=timeout,
    )
