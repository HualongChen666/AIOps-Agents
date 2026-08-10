# -*- coding: utf-8 -*-
"""
Enhanced Retry Mechanism

🔧 P0 Reliability Enhancement:
- Advanced retry strategies with exponential backoff
- Jitter to prevent thundering herd
- Circuit breaker integration
- Deadline/timeout support
- Retry condition customization
"""

from loguru import logger
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
from functools import wraps
import time
import asyncio
import secrets

_random = secrets.SystemRandom()


class RetryStrategy:
    """Retry strategy configuration"""

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    IMMEDIATE = "immediate"


class RetryCondition:
    """Retry condition predicates"""

    @staticmethod
    def is_retryable_exception(exception: Exception) -> bool:
        """Check if exception is retryable"""
        # Network-related errors
        retryable_errors = (
            ConnectionError,
            TimeoutError,
            OSError,
            IOError,
        )
        return isinstance(exception, retryable_errors)

    @staticmethod
    def is_server_error(exception: Exception) -> bool:
        """Check if exception represents a server error (5xx)"""
        if hasattr(exception, "status_code"):
            return 500 <= getattr(exception, "status_code", 0) < 600
        return False

    @staticmethod
    def is_rate_limited(exception: Exception) -> bool:
        """Check if exception represents rate limiting (429)"""
        if hasattr(exception, "status_code"):
            return getattr(exception, "status_code", 0) == 429
        return False

    @staticmethod
    def custom_condition(
        condition_func: Callable[[Exception], bool],
    ) -> Callable[[Exception], bool]:
        """Create custom retry condition"""
        return condition_func


class EnhancedRetry:
    """Enhanced retry mechanism with advanced features"""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: str = RetryStrategy.EXPONENTIAL_BACKOFF,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        jitter_range: float = 0.1,
        retry_on: Optional[Callable[[Exception], bool]] = None,
        retry_on_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
        deadline: Optional[float] = None,
        on_retry_callback: Optional[Callable[[int, Exception, float], None]] = None,
    ):
        """
        Initialize enhanced retry mechanism.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            strategy: Retry strategy (exponential_backoff, linear_backoff, fixed_delay, immediate)
            backoff_multiplier: Multiplier for exponential/linear backoff
            jitter: Add random jitter to prevent thundering herd
            jitter_range: Jitter range as fraction of delay (0.0 to 1.0)
            retry_on: Custom function to determine if exception is retryable
            retry_on_exceptions: Tuple of exception types to retry on
            deadline: Overall deadline for all attempts in seconds
            on_retry_callback: Callback function called on each retry (attempt, exception, delay)
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retry_on = retry_on
        self.retry_on_exceptions = retry_on_exceptions
        self.deadline = deadline
        self.on_retry_callback = on_retry_callback

        logger.info(
            f"Enhanced retry initialized: max_attempts={max_attempts}, "
            f"strategy={strategy}, base_delay={base_delay}s, max_delay={max_delay}s"
        )

    def should_retry(self, exception: Exception) -> bool:
        """Determine if operation should be retried based on exception"""
        # Check custom retry condition first
        if self.retry_on and not self.retry_on(exception):
            return False

        # Check specific exception types
        if self.retry_on_exceptions:
            return isinstance(exception, self.retry_on_exceptions)

        # Default retryable conditions
        return (
            RetryCondition.is_retryable_exception(exception)
            or RetryCondition.is_server_error(exception)
            or RetryCondition.is_rate_limited(exception)
        )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay before next retry"""
        if self.strategy == RetryStrategy.IMMEDIATE:
            delay = 0.0
        elif self.strategy == RetryStrategy.FIXED_DELAY:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = min(
                self.base_delay * (1 + (attempt - 1) * self.backoff_multiplier), self.max_delay
            )
        else:  # EXPONENTIAL_BACKOFF (default)
            delay = min(
                self.base_delay * (self.backoff_multiplier ** (attempt - 1)), self.max_delay
            )

        # Add jitter if enabled
        if self.jitter and delay > 0:
            jitter_amount = delay * self.jitter_range
            delay = delay + _random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.0, delay)  # Ensure non-negative

        return delay

    def __call__(self, func: Callable) -> Callable:
        """Decorator to apply retry mechanism to function"""
        if asyncio.iscoroutinefunction(func):
            return self._async_wrapper(func)
        else:
            return self._sync_wrapper(func)

    def _async_wrapper(self, func: Callable) -> Callable:
        """Async wrapper for retry mechanism"""

        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    # Check deadline
                    if self.deadline:
                        elapsed = time.time() - start_time
                        if elapsed >= self.deadline:
                            raise TimeoutError(f"Retry deadline exceeded after {elapsed:.2f}s")

                    # Execute function
                    result = await func(*args, **kwargs)

                    # Success - return result
                    if attempt > 1:
                        logger.info(f"Retry succeeded on attempt {attempt}/{self.max_attempts}")
                    return result

                except Exception as e:
                    last_exception = e

                    # Check if should retry
                    if not self.should_retry(e) or attempt >= self.max_attempts:
                        logger.error(
                            f"Retry failed after {attempt}/{self.max_attempts} attempts: "
                            f"{type(e).__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = self.calculate_delay(attempt)

                    # Call retry callback if provided
                    if self.on_retry_callback:
                        try:
                            self.on_retry_callback(attempt, e, delay)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")

                    # Log retry
                    logger.warning(
                        f"Retry attempt {attempt}/{self.max_attempts} failed: {type(e).__name__}: {e}. "  # noqa: E501
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Wait before retry
                    if delay > 0:
                        await asyncio.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    def _sync_wrapper(self, func: Callable) -> Callable:
        """Sync wrapper for retry mechanism"""

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            last_exception = None

            for attempt in range(1, self.max_attempts + 1):
                try:
                    # Check deadline
                    if self.deadline:
                        elapsed = time.time() - start_time
                        if elapsed >= self.deadline:
                            raise TimeoutError(f"Retry deadline exceeded after {elapsed:.2f}s")

                    # Execute function
                    result = func(*args, **kwargs)

                    # Success - return result
                    if attempt > 1:
                        logger.info(f"Retry succeeded on attempt {attempt}/{self.max_attempts}")
                    return result

                except Exception as e:
                    last_exception = e

                    # Check if should retry
                    if not self.should_retry(e) or attempt >= self.max_attempts:
                        logger.error(
                            f"Retry failed after {attempt}/{self.max_attempts} attempts: "
                            f"{type(e).__name__}: {e}"
                        )
                        raise

                    # Calculate delay
                    delay = self.calculate_delay(attempt)

                    # Call retry callback if provided
                    if self.on_retry_callback:
                        try:
                            self.on_retry_callback(attempt, e, delay)
                        except Exception as callback_error:
                            logger.warning(f"Retry callback failed: {callback_error}")

                    # Log retry
                    logger.warning(
                        f"Retry attempt {attempt}/{self.max_attempts} failed: {type(e).__name__}: {e}. "  # noqa: E501
                        f"Retrying in {delay:.2f}s..."
                    )

                    # Wait before retry
                    if delay > 0:
                        time.sleep(delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

        return wrapper


def retry_with_enhanced_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    strategy: str = RetryStrategy.EXPONENTIAL_BACKOFF,
    backoff_multiplier: float = 2.0,
    jitter: bool = True,
    retry_on_exceptions: Optional[Tuple[Type[Exception], ...]] = None,
    deadline: Optional[float] = None,
):
    """
    Convenience decorator for enhanced retry mechanism.

    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        strategy: Retry strategy
        backoff_multiplier: Multiplier for backoff
        jitter: Add random jitter
        retry_on_exceptions: Tuple of exception types to retry on
        deadline: Overall deadline for all attempts in seconds

    Usage:
        @retry_with_enhanced_retry(max_attempts=3, base_delay=1.0)
        async def external_api_call():
            # Your code here
            pass
    """
    enhanced_retry = EnhancedRetry(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        strategy=strategy,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retry_on_exceptions=retry_on_exceptions,
        deadline=deadline,
    )
    return enhanced_retry


class RetryMetrics:
    """Metrics collection for retry operations"""

    def __init__(self):
        self.attempt_counts: Dict[str, List[int]] = {}
        self.failure_counts: Dict[str, int] = {}
        self.success_counts: Dict[str, int] = {}
        self.total_retry_delay: Dict[str, float] = {}

    def record_attempt(self, operation_name: str, attempt_number: int, delay: float):
        """Record a retry attempt"""
        if operation_name not in self.attempt_counts:
            self.attempt_counts[operation_name] = []
        self.attempt_counts[operation_name].append(attempt_number)

        if operation_name not in self.total_retry_delay:
            self.total_retry_delay[operation_name] = 0.0
        self.total_retry_delay[operation_name] += delay

    def record_success(self, operation_name: str):
        """Record a successful operation"""
        if operation_name not in self.success_counts:
            self.success_counts[operation_name] = 0
        self.success_counts[operation_name] += 1

    def record_failure(self, operation_name: str):
        """Record a failed operation"""
        if operation_name not in self.failure_counts:
            self.failure_counts[operation_name] = 0
        self.failure_counts[operation_name] += 1

    def get_metrics(self, operation_name: str) -> Dict[str, Any]:
        """Get metrics for a specific operation"""
        attempts = self.attempt_counts.get(operation_name, [])
        return {
            "operation": operation_name,
            "total_attempts": len(attempts),
            "average_attempts": sum(attempts) / len(attempts) if attempts else 0,
            "max_attempts": max(attempts) if attempts else 0,
            "success_count": self.success_counts.get(operation_name, 0),
            "failure_count": self.failure_counts.get(operation_name, 0),
            "total_retry_delay": self.total_retry_delay.get(operation_name, 0.0),
            "average_retry_delay": (
                self.total_retry_delay.get(operation_name, 0.0) / len(attempts) if attempts else 0.0
            ),
        }

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all operations"""
        all_operations = (
            set(self.attempt_counts.keys())
            | set(self.success_counts.keys())
            | set(self.failure_counts.keys())
        )
        return {op: self.get_metrics(op) for op in all_operations}


# Global retry metrics instance
retry_metrics = RetryMetrics()
