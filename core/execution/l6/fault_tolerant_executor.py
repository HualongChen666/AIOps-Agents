# -*- coding: utf-8 -*-
import logging
"""
L6 Execution Layer - Fault Tolerant Executor (Phase 2)
Enhanced execution engine with comprehensive fault tolerance and recovery mechanisms
"""

import asyncio
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class ExecutionStatus(Enum):
    """Execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class FailureType(Enum):
    """Failure type classification"""

    NETWORK_ERROR = "network_error"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    LOGIC_ERROR = "logic_error"
    DEPENDENCY_ERROR = "dependency_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class ExecutionResult:
    """Execution result"""

    status: ExecutionStatus
    result: Optional[Any] = None
    error: Optional[Exception] = None
    retry_count: int = 0
    execution_time: float = 0.0
    failure_type: Optional[FailureType] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RetryPolicy:
    """Retry policy configuration"""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_backoff: bool = True
    retryable_exceptions: List[type] = field(default_factory=list)
    non_retryable_exceptions: List[type] = field(default_factory=list)


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""

    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    monitor_window: float = 300.0


class CircuitBreakerState(Enum):
    """Circuit breaker state"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, blocking calls
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreaker:
    """Circuit breaker for fault tolerance"""

    def __init__(self, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker

        Args:
            config: Circuit breaker configuration
        """
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_success_count = 0
        self.lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        async with self.lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker transitioning to HALF_OPEN")
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )

                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.half_open_success_count += 1
                    if self.half_open_success_count >= self.config.half_open_max_calls:
                        self._reset()
                        logger.info("Circuit breaker reset to CLOSED")

                return result

            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                self._record_failure()
                raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset"""
        if self.last_failure_time is None:
            return True

        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout

    def _record_failure(self):
        """Record a failure"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")

    def _reset(self):
        """Reset circuit breaker"""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.half_open_success_count = 0

    def get_state(self) -> CircuitBreakerState:
        """Get current circuit breaker state"""
        return self.state


class FaultTolerantExecutor:
    """Fault tolerant executor with comprehensive error handling and recovery"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize fault tolerant executor

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Retry policy
        self.retry_policy = RetryPolicy(
            max_retries=self.config.get("max_retries", 3),
            base_delay=self.config.get("base_delay", 1.0),
            max_delay=self.config.get("max_delay", 60.0),
            exponential_backoff=self.config.get("exponential_backoff", True),
        )

        # Circuit breaker
        self.circuit_breaker_config = CircuitBreakerConfig(
            failure_threshold=self.config.get("circuit_breaker_failure_threshold", 5),
            recovery_timeout=self.config.get("circuit_breaker_recovery_timeout", 60.0),
            half_open_max_calls=self.config.get("circuit_breaker_half_open_max_calls", 3),
        )
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Execution metrics
        self.execution_metrics: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total": 0,
                "success": 0,
                "failure": 0,
                "retry": 0,
                "timeout": 0,
                "avg_duration": 0.0,
            }
        )

        # Timeout configuration
        self.default_timeout = self.config.get("default_timeout", 30.0)

        # Fallback handlers
        self.fallback_handlers: Dict[str, Callable] = {}

        logger.info("Fault tolerant executor initialized")

    def register_fallback(self, operation: str, handler: Callable) -> None:
        """
        Register fallback handler for an operation

        Args:
            operation: Operation name
            handler: Fallback handler function
        """
        self.fallback_handlers[operation] = handler
        logger.info(f"Registered fallback handler for operation: {operation}")

    def get_circuit_breaker(self, operation: str) -> CircuitBreaker:
        """
        Get or create circuit breaker for operation

        Args:
            operation: Operation name

        Returns:
            CircuitBreaker: Circuit breaker instance
        """
        if operation not in self.circuit_breakers:
            self.circuit_breakers[operation] = CircuitBreaker(self.circuit_breaker_config)

        return self.circuit_breakers[operation]

    async def execute(
        self,
        func: Callable,
        operation: str,
        *args,
        timeout: Optional[float] = None,
        retry_policy: Optional[RetryPolicy] = None,
        circuit_breaker_enabled: bool = True,
        **kwargs,
    ) -> ExecutionResult:
        """
        Execute function with fault tolerance mechanisms

        Args:
            func: Function to execute
            operation: Operation name for tracking
            *args: Function arguments
            timeout: Execution timeout in seconds
            retry_policy: Custom retry policy
            circuit_breaker_enabled: Enable circuit breaker
            **kwargs: Function keyword arguments

        Returns:
            ExecutionResult: Execution result
        """
        start_time = time.time()
        actual_timeout = timeout or self.default_timeout
        actual_retry_policy = retry_policy or self.retry_policy

        # Update metrics
        self.execution_metrics[operation]["total"] += 1

        try:
            # Circuit breaker protection
            if circuit_breaker_enabled:
                circuit_breaker = self.get_circuit_breaker(operation)
                result = await self._execute_with_circuit_breaker(
                    circuit_breaker,
                    func,
                    operation,
                    actual_timeout,
                    actual_retry_policy,
                    *args,
                    **kwargs,
                )
            else:
                result = await self._execute_with_retry(
                    func, operation, actual_timeout, actual_retry_policy, *args, **kwargs
                )

            # Update success metrics
            execution_time = time.time() - start_time
            self.execution_metrics[operation]["success"] += 1
            self._update_avg_duration(operation, execution_time)

            return ExecutionResult(
                status=ExecutionStatus.COMPLETED,
                result=result,
                execution_time=execution_time,
                metadata={"operation": operation},
            )

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            self.execution_metrics[operation]["timeout"] += 1

            # Try fallback
            fallback_result = await self._try_fallback(operation, args, kwargs)
            if fallback_result is not None:
                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    result=fallback_result,
                    execution_time=execution_time,
                    failure_type=FailureType.TIMEOUT_ERROR,
                    metadata={"operation": operation, "fallback_used": True},
                )

            return ExecutionResult(
                status=ExecutionStatus.TIMEOUT,
                error=Exception("Execution timeout"),
                execution_time=execution_time,
                failure_type=FailureType.TIMEOUT_ERROR,
                metadata={"operation": operation},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.execution_metrics[operation]["failure"] += 1

            # Classify failure type
            failure_type = self._classify_error(e)

            # Try fallback
            fallback_result = await self._try_fallback(operation, args, kwargs)
            if fallback_result is not None:
                return ExecutionResult(
                    status=ExecutionStatus.COMPLETED,
                    result=fallback_result,
                    execution_time=execution_time,
                    failure_type=failure_type,
                    metadata={"operation": operation, "fallback_used": True},
                )

            return ExecutionResult(
                status=ExecutionStatus.FAILED,
                error=e,
                execution_time=execution_time,
                failure_type=failure_type,
                metadata={"operation": operation},
            )

    async def _execute_with_circuit_breaker(
        self,
        circuit_breaker: CircuitBreaker,
        func: Callable,
        operation: str,
        timeout: float,
        retry_policy: RetryPolicy,
        *args,
        **kwargs,
    ) -> Any:
        """Execute with circuit breaker protection"""

        async def protected_call():
            return await self._execute_with_retry(
                func, operation, timeout, retry_policy, *args, **kwargs
            )

        return await circuit_breaker.call(protected_call)

    async def _execute_with_retry(
        self,
        func: Callable,
        operation: str,
        timeout: float,
        retry_policy: RetryPolicy,
        *args,
        **kwargs,
    ) -> Any:
        """Execute with retry logic"""
        last_exception: Optional[Exception] = None

        for attempt in range(retry_policy.max_retries + 1):
            try:
                # Execute with timeout
                result = await asyncio.wait_for(
                    self._call_function(func, *args, **kwargs), timeout=timeout
                )

                if attempt > 0:
                    self.execution_metrics[operation]["retry"] += 1
                    logger.info(f"Operation {operation} succeeded on attempt {attempt + 1}")

                return result

            except asyncio.TimeoutError as e:
                last_exception = e
                logger.warning(f"Operation {operation} timeout on attempt {attempt + 1}")

            except Exception as e:
                last_exception = e

                # Check if exception is retryable
                if not self._is_retryable(e, retry_policy):
                    logger.error(f"Operation {operation} failed with non-retryable error: {e}")
                    raise

                logger.warning(f"Operation {operation} failed on attempt {attempt + 1}: {e}")

            # Calculate delay for next retry
            if attempt < retry_policy.max_retries:
                delay = self._calculate_retry_delay(attempt, retry_policy)
                logger.info(f"Retrying operation {operation} in {delay:.2f}s...")
                await asyncio.sleep(delay)

        raise last_exception or Exception("Max retries exceeded")

    async def _call_function(self, func: Callable, *args, **kwargs) -> Any:
        """Call function with proper async handling"""
        if asyncio.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)

    def _calculate_retry_delay(self, attempt: int, retry_policy: RetryPolicy) -> float:
        """Calculate retry delay with exponential backoff"""
        if retry_policy.exponential_backoff:
            delay: float = retry_policy.base_delay * (2**attempt)
        else:
            delay = retry_policy.base_delay

        return min(delay, retry_policy.max_delay)

    def _is_retryable(self, exception: Exception, retry_policy: RetryPolicy) -> bool:
        """Check if exception is retryable"""
        # Check non-retryable exceptions
        for exc_type in retry_policy.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False

        # Check retryable exceptions
        if retry_policy.retryable_exceptions:
            for exc_type in retry_policy.retryable_exceptions:
                if isinstance(exception, exc_type):
                    return True

        # Default retryable exceptions
        return isinstance(exception, (asyncio.TimeoutError, ConnectionError, TimeoutError))

    def _classify_error(self, exception: Exception) -> FailureType:
        """Classify error type"""
        if isinstance(exception, (ConnectionError, ConnectionRefusedError)):
            return FailureType.NETWORK_ERROR
        elif isinstance(exception, (asyncio.TimeoutError, TimeoutError)):
            return FailureType.TIMEOUT_ERROR
        elif isinstance(exception, (MemoryError, ResourceWarning)):
            return FailureType.RESOURCE_ERROR
        elif isinstance(exception, (ImportError, AttributeError)):
            return FailureType.DEPENDENCY_ERROR
        else:
            return FailureType.LOGIC_ERROR

    async def _try_fallback(self, operation: str, args: tuple, kwargs: dict) -> Optional[Any]:
        """Try fallback handler"""
        if operation in self.fallback_handlers:
            try:
                fallback_handler = self.fallback_handlers[operation]
                if asyncio.iscoroutinefunction(fallback_handler):
                    return await fallback_handler(*args, **kwargs)
                else:
                    return fallback_handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"Fallback handler for {operation} failed: {e}")

        return None

    def _update_avg_duration(self, operation: str, duration: float):
        """Update average execution duration"""
        metrics = self.execution_metrics[operation]
        total = metrics["total"]
        if total > 0:
            metrics["avg_duration"] = (metrics["avg_duration"] * (total - 1) + duration) / total

    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution metrics

        Args:
            operation: Specific operation name, or None for all operations

        Returns:
            Metrics dictionary
        """
        if operation:
            return dict(self.execution_metrics[operation])
        else:
            return {op: dict(metrics) for op, metrics in self.execution_metrics.items()}

    def get_circuit_breaker_states(self) -> Dict[str, str]:
        """Get all circuit breaker states"""
        return {op: cb.get_state().value for op, cb in self.circuit_breakers.items()}

    def reset_circuit_breaker(self, operation: str) -> bool:
        """
        Reset circuit breaker for operation

        Args:
            operation: Operation name

        Returns:
            Success status
        """
        if operation in self.circuit_breakers:
            self.circuit_breakers[operation]._reset()
            logger.info(f"Circuit breaker reset for operation: {operation}")
            return True
        return False


def get_fault_tolerant_executor(config: Optional[Dict[str, Any]] = None) -> FaultTolerantExecutor:
    """
    Factory function to get fault tolerant executor instance

    Args:
        config: Optional configuration dictionary

    Returns:
        FaultTolerantExecutor: Executor instance
    """
    return FaultTolerantExecutor(config)