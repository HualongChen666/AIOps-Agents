# -*- coding: utf-8 -*-
"""Resilience decorators for Phase 3: retry, circuit breaker, fallback."""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import time
from typing import Any, Callable, Coroutine, Optional, Tuple, Type, TypeVar, Union

F = TypeVar("F", bound=Callable[..., Any])

logger = logging.getLogger(__name__)


def _is_async(func: Callable[..., Any]) -> bool:
    return inspect.iscoroutinefunction(func)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
) -> Callable[[F], F]:
    """Retry an operation with exponential backoff."""

    def decorator(func: F) -> F:
        if _is_async(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except exceptions as exc:
                        if attempt == max_retries:
                            raise
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            "%s failed (attempt %s/%s): %s. Retrying in %ss",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            exc,
                            delay,
                        )
                        if on_retry:
                            try:
                                on_retry(exc, attempt + 1)
                            except Exception as e:
                                logging.exception("Unexpected exception: %s", e)
                        await asyncio.sleep(delay)
                return None  # pragma: no cover

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as exc:
                        if attempt == max_retries:
                            raise
                        delay = base_delay * (2**attempt)
                        logger.warning(
                            "%s failed (attempt %s/%s): %s. Retrying in %ss",
                            func.__name__,
                            attempt + 1,
                            max_retries + 1,
                            exc,
                            delay,
                        )
                        if on_retry:
                            try:
                                on_retry(exc, attempt + 1)
                            except Exception as e:
                                logging.exception("Unexpected exception: %s", e)
                        time.sleep(delay)
                return None  # pragma: no cover

            return sync_wrapper  # type: ignore[return-value]

    return decorator


class CircuitBreaker:
    """Simple in-memory circuit breaker."""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "circuit",
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.name = name
        self.failures = 0
        self.last_failure_time = 0.0
        self.open = False

    def _is_open(self) -> bool:
        if not self.open:
            return False
        if time.time() - self.last_failure_time >= self.recovery_timeout:
            self.open = False
            self.failures = 0
            logger.info("Circuit breaker %s moved to HALF-OPEN", self.name)
            return False
        return True

    def record_success(self) -> None:
        self.failures = 0
        if self.open:
            self.open = False
            logger.info("Circuit breaker %s CLOSED", self.name)

    def record_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.open = True
            logger.warning(
                "Circuit breaker %s OPEN after %s failures",
                self.name,
                self.failures,
            )

    def call(self, func: F, *args: Any, **kwargs: Any) -> Any:
        if self._is_open():
            raise RuntimeError(f"Circuit breaker {self.name} is OPEN")
        result = func(*args, **kwargs)
        self.record_success()
        return result

    async def call_async(self, func: F, *args: Any, **kwargs: Any) -> Any:
        if self._is_open():
            raise RuntimeError(f"Circuit breaker {self.name} is OPEN")
        if _is_async(func):
            result = await func(*args, **kwargs)
        else:
            result = func(*args, **kwargs)
        self.record_success()
        return result


def circuit_breaker(
    failure_threshold: int = 5, recovery_timeout: float = 60.0, name: str = "circuit"
) -> Callable[[F], F]:
    """Circuit breaker decorator (sync/async)."""
    cb = CircuitBreaker(failure_threshold, recovery_timeout, name)

    def decorator(func: F) -> F:
        if _is_async(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                return await cb.call_async(func, *args, **kwargs)

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                return cb.call(func, *args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator


def fallback_on_error(
    fallback: Callable[..., Any],
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    log_warning: bool = True,
) -> Callable[[F], F]:
    """Fallback to another callable when the wrapped function fails."""

    def decorator(func: F) -> F:
        if _is_async(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    if log_warning:
                        logger.warning("%s failed (%s), using fallback", func.__name__, exc)
                    return (
                        await fallback(*args, **kwargs)
                        if _is_async(fallback)
                        else fallback(*args, **kwargs)
                    )

            return async_wrapper  # type: ignore[return-value]
        else:

            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if log_warning:
                        logger.warning("%s failed (%s), using fallback", func.__name__, exc)
                    return fallback(*args, **kwargs)

            return sync_wrapper  # type: ignore[return-value]

    return decorator
