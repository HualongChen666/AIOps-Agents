# -*- coding: utf-8 -*-
"""
Advanced Error Handling Module
高级错误处理模块

提供重试机制、断路器、错误恢复等高级错误处理功能。
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """断路器状态"""

    CLOSED = "closed"  # 正常工作
    OPEN = "open"  # 断路打开，拒绝请求
    HALF_OPEN = "half_open"  # 半开状态，尝试恢复


@dataclass
class CircuitBreakerConfig:
    """断路器配置"""

    failure_threshold: int = 5  # 失败阈值
    recovery_timeout: int = 60  # 恢复超时（秒）
    expected_exception: Type[Exception] = Exception  # 预期的异常类型


class CircuitBreaker:
    """断路器实现"""

    def __init__(self, config: CircuitBreakerConfig):
        """
        初始化断路器

        Args:
            config: 断路器配置
        """
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        通过断路器调用函数

        Args:
            func: 要调用的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果

        Raises:
            CircuitBreakerOpenError: 断路器打开时
        """
        async with self._lock:
            # 检查断路器状态
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError("Circuit breaker is OPEN")

            elif self.state == CircuitState.HALF_OPEN:
                logger.info("Circuit breaker in HALF_OPEN, attempting call")

        try:
            # 执行函数
            result = await func(*args, **kwargs)

            # 成功时重置断路器
            async with self._lock:
                self.failure_count = 0
                if self.state == CircuitState.HALF_OPEN:
                    self.state = CircuitState.CLOSED
                    logger.info("Circuit breaker reset to CLOSED")

            return result

        except self.config.expected_exception:
            # 失败时增加失败计数
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = datetime.now(timezone.utc)

                # 达到阈值时打开断路器
                if self.failure_count >= self.config.failure_threshold:
                    self.state = CircuitState.OPEN
                    logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

            raise

    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        if self.last_failure_time is None:
            return True

        elapsed = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    def get_state(self) -> CircuitState:
        """获取断路器状态"""
        return self.state

    def get_stats(self) -> Dict[str, Any]:
        """获取断路器统计信息"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "failure_threshold": self.config.failure_threshold,
            "recovery_timeout": self.config.recovery_timeout,
        }


class CircuitBreakerOpenError(Exception):
    """断路器打开异常"""


class RetryConfig:
    """重试配置"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: Optional[List[Type[Exception]]] = None,
    ):
        """
        初始化重试配置

        Args:
            max_attempts: 最大重试次数
            base_delay: 基础延迟（秒）
            max_delay: 最大延迟（秒）
            exponential_base: 指数退避基数
            jitter: 是否添加随机抖动
            retryable_exceptions: 可重试的异常类型
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or [Exception]


class RetryPolicy:
    """重试策略"""

    def __init__(self, config: RetryConfig):
        """
        初始化重试策略

        Args:
            config: 重试配置
        """
        self.config = config

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            exception: 发生的异常
            attempt: 当前尝试次数

        Returns:
            是否应该重试
        """
        # 检查是否超过最大尝试次数
        if attempt >= self.config.max_attempts:
            return False

        # 检查异常是否可重试
        if self.config.retryable_exceptions:
            return isinstance(exception, tuple(self.config.retryable_exceptions))

        return True

    def calculate_delay(self, attempt: int) -> float:
        """
        计算重试延迟

        Args:
            attempt: 当前尝试次数

        Returns:
            延迟时间（秒）
        """
        # 指数退避
        delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))

        # 限制最大延迟
        delay = min(delay, self.config.max_delay)

        # 添加随机抖动
        if self.config.jitter:
            import random

            delay = delay * (0.5 + random.random() * 0.5)  # nosec B311

        return delay


async def retry_with_policy(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """
    使用重试策略执行函数

    Args:
        func: 要执行的函数
        config: 重试配置
        *args: 函数参数
        **kwargs: 函数关键字参数

    Returns:
        函数执行结果
    """
    policy = RetryPolicy(config)

    for attempt in range(1, config.max_attempts + 1):
        try:
            if attempt > 1:
                delay = policy.calculate_delay(attempt)
                logger.info(f"Retry attempt {attempt}/{config.max_attempts}, delay: {delay:.2f}s")
                await asyncio.sleep(delay)

            return await func(*args, **kwargs)

        except Exception as e:
            if policy.should_retry(e, attempt):
                logger.warning(
                    f"Attempt {attempt} failed: {type(e).__name__}: {str(e)}, "
                    f"will retry in {policy.calculate_delay(attempt + 1):.2f}s"
                )
            else:
                logger.error(
                    f"All {config.max_attempts} attempts failed, "
                    f"last error: {type(e).__name__}: {str(e)}"
                )
                raise


def retry_decorator(config: RetryConfig):
    """
    重试装饰器

    Args:
        config: 重试配置

    Returns:
        装饰器函数
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_with_policy(func, config, *args, **kwargs)

        return wrapper

    return decorator


class ErrorRecoveryManager:
    """错误恢复管理器"""

    def __init__(self):
        """初始化错误恢复管理器"""
        self._recovery_strategies: Dict[str, Callable] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """
        注册错误恢复策略

        Args:
            error_type: 错误类型
            strategy: 恢复策略函数
        """
        self._recovery_strategies[error_type] = strategy
        logger.info(f"Registered recovery strategy for: {error_type}")

    def register_circuit_breaker(self, name: str, config: CircuitBreakerConfig):
        """
        注册断路器

        Args:
            name: 断路器名称
            config: 断路器配置
        """
        self._circuit_breakers[name] = CircuitBreaker(config)
        logger.info(f"Registered circuit breaker: {name}")

    async def execute_with_circuit_breaker(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """
        使用断路器执行函数

        Args:
            name: 断路器名称
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 函数关键字参数

        Returns:
            函数执行结果
        """
        if name not in self._circuit_breakers:
            logger.warning(f"Circuit breaker not found: {name}, executing without circuit breaker")
            return await func(*args, **kwargs)

        circuit_breaker = self._circuit_breakers[name]
        return await circuit_breaker.call(func, *args, **kwargs)

    async def attempt_recovery(self, error: Exception) -> bool:
        """
        尝试错误恢复

        Args:
            error: 发生的错误

        Returns:
            是否恢复成功
        """
        error_type = type(error).__name__

        if error_type in self._recovery_strategies:
            strategy = self._recovery_strategies[error_type]
            try:
                logger.info(f"Attempting recovery for {error_type}")
                result = await strategy(error)
                logger.info(f"Recovery successful for {error_type}")
                return bool(result)
            except Exception as e:
                logger.error(f"Recovery failed for {error_type}: {e}")
                return False
        else:
            logger.warning(f"No recovery strategy found for {error_type}")
            return False

    def get_circuit_breaker_stats(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取断路器统计信息

        Args:
            name: 断路器名称

        Returns:
            断路器统计信息
        """
        if name in self._circuit_breakers:
            return self._circuit_breakers[name].get_stats()
        return None


# 全局错误恢复管理器实例
error_recovery_manager = ErrorRecoveryManager()


# 注册默认的断路器
error_recovery_manager.register_circuit_breaker(
    "database",
    CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60, expected_exception=Exception),
)

error_recovery_manager.register_circuit_breaker(
    "api",
    CircuitBreakerConfig(failure_threshold=10, recovery_timeout=30, expected_exception=Exception),
)


async def setup_error_recovery():
    """
    设置错误恢复机制

    Returns:
        设置结果
    """

    try:
        # 注册默认的恢复策略
        async def database_recovery(error: Exception) -> bool:
            """数据库恢复策略"""
            # 尝试重新连接数据库
            from sqlalchemy import text

            from core.db_engine import AsyncSessionLocal

            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
                logger.info("Database recovery successful")
                return True
            except Exception as e:
                logger.error(f"Database recovery failed: {e}")
                return False

        async def cache_recovery(error: Exception) -> bool:
            """缓存恢复策略"""
            # 清除缓存并重试
            from core.query_optimization import query_cache

            query_cache.invalidate()
            logger.info("Cache recovery: cache invalidated")
            return True

        error_recovery_manager.register_recovery_strategy("DatabaseError", database_recovery)
        error_recovery_manager.register_recovery_strategy("CacheError", cache_recovery)

        logger.info("Error recovery setup completed")

        return {
            "status": "success",
            "circuit_breakers": list(error_recovery_manager._circuit_breakers.keys()),
            "recovery_strategies": list(error_recovery_manager._recovery_strategies.keys()),
        }

    except Exception as e:
        logger.error(f"Error recovery setup failed: {e}")
        return {"status": "error", "error": str(e)}
