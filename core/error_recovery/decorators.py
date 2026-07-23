# -*- coding: utf-8 -*-
"""
错误恢复策略装饰器模块

提供重试、降级、熔断等恢复策略的装饰器。
"""

import time
from functools import wraps
from typing import Callable, Optional

from core.exceptions import (
    DatabaseException,
    ExternalServiceException,
    NetworkException,
)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    multiplier: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    重试装饰器（带指数退避）

    Args:
        max_attempts: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        multiplier: 延迟倍数
        exceptions: 需要重试的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = min(base_delay * (multiplier**attempt), max_delay)
                        time.sleep(delay)
            raise last_exception  # type: ignore[misc]

        return wrapper

    return decorator


def fallback_on_error(fallback_func: Callable, exceptions: tuple = (Exception,)):
    """
    降级装饰器

    Args:
        fallback_func: 降级函数
        exceptions: 需要降级的异常类型

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except exceptions:
                return fallback_func(*args, **kwargs)

        return wrapper

    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: int = 60,
    exceptions: tuple = (Exception,),
):
    """
    熔断器装饰器

    Args:
        failure_threshold: 失败阈值
        success_threshold: 成功阈值
        timeout: 超时时间（秒）
        exceptions: 需要熔断的异常类型

    Returns:
        装饰器函数
    """

    class CircuitBreakerState:
        def __init__(self):
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None
            self.state = "closed"  # closed, open, half-open

    state = CircuitBreakerState()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()

            # 检查熔断器状态
            if state.state == "open":
                if current_time - state.last_failure_time > timeout:  # type: ignore[operator]
                    state.state = "half-open"
                    state.success_count = 0
                else:
                    raise Exception("Circuit breaker is open")

            try:
                result = func(*args, **kwargs)
                # 成功
                if state.state == "half-open":
                    state.success_count += 1
                    if state.success_count >= success_threshold:
                        state.state = "closed"
                        state.failure_count = 0
                else:
                    state.failure_count = 0
                return result
            except exceptions:
                # 失败
                state.failure_count += 1
                state.last_failure_time = current_time
                if state.failure_count >= failure_threshold:
                    state.state = "open"
                raise

        return wrapper

    return decorator


def timeout(seconds: int, default_value: Optional[any] = None):  # type: ignore[valid-type]
    """
    超时装饰器

    Args:
        seconds: 超时时间（秒）
        default_value: 超时后的默认返回值

    Returns:
        装饰器函数
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import signal

            def timeout_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds} seconds")

            # 设置信号处理器
            sig = signal.SIGALRM  # type: ignore[attr-defined]
            old_handler = signal.signal(sig, timeout_handler)  # type: ignore[attr-defined]
            signal.alarm(seconds)  # type: ignore[attr-defined]

            try:
                result = func(*args, **kwargs)
                signal.alarm(0)  # type: ignore[attr-defined]  # 取消闹钟
                return result
            except TimeoutError:
                signal.alarm(0)  # type: ignore[attr-defined]  # 取消闹钟
                if default_value is not None:
                    return default_value
                raise
            finally:
                signal.signal(signal.SIGALRM, old_handler)  # type: ignore[attr-defined]  # 恢复旧处理器

        return wrapper

    return decorator


def retry_database(max_attempts: int = 3):
    """
    数据库重试装饰器

    Args:
        max_attempts: 最大重试次数

    Returns:
        装饰器函数
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        base_delay=0.5,
        max_delay=5.0,
        multiplier=2.0,
        exceptions=(DatabaseException,),
    )


def retry_external_service(max_attempts: int = 3):
    """
    外部服务重试装饰器

    Args:
        max_attempts: 最大重试次数

    Returns:
        装饰器函数
    """
    return retry_with_backoff(
        max_attempts=max_attempts,
        base_delay=1.0,
        max_delay=10.0,
        multiplier=2.0,
        exceptions=(ExternalServiceException, NetworkException),
    )
