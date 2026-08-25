# -*- coding: utf-8 -*-
"""
Common Logging Helpers
======================

Provides reusable logging patterns and utilities to reduce
code duplication across API routers.

This module addresses the following code duplication issues:
- Repeated log message formatting patterns
- Repeated request logging patterns
- Repeated error logging patterns
- Repeated operation logging patterns
"""

import logging
from typing import Any, Optional

from fastapi import Request

logger = logging.getLogger(__name__)


def log_request_received(operation_name: str, request: Optional[Request] = None, **params) -> None:
    """
    Log that a request was received with standardized formatting.

    This function reduces duplication of request logging patterns.

    Args:
        operation_name: Name of the operation
        request: FastAPI request object (optional)
        **params: Additional parameters to log

    Example:
        log_request_received(
            "get_alerts",
            request,
            limit=20,
            tenant_id="tenant123"
        )
    """
    client_ip = request.client.host if request and request.client else "unknown"
    param_str = " | ".join(f"{k}={v}" for k, v in params.items())
    logger.info(f"请求 {operation_name} | client={client_ip} | {param_str}")


def log_request_success(
    operation_name: str, result_info: Optional[dict[str, Any]] = None, **extra
) -> None:
    """
    Log that a request completed successfully.

    This function reduces duplication of success logging patterns.

    Args:
        operation_name: Name of the operation
        result_info: Dictionary with result information to log
        **extra: Additional fields to log

    Example:
        log_request_success(
            "get_alerts",
            result_info={"count": 42, "cached": True}
        )
    """
    if result_info:
        result_str = " | ".join(f"{k}={v}" for k, v in result_info.items())
        logger.info(f"{operation_name} 成功 | {result_str}")
    else:
        logger.info(f"{operation_name} 成功")

    if extra:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
        logger.debug(f"{operation_name} 额外信息 | {extra_str}")


def log_request_error(
    operation_name: str, error: Exception, include_traceback: bool = True, **context
) -> None:
    """
    Log that a request failed with error details.

    This function reduces duplication of error logging patterns.

    Args:
        operation_name: Name of the operation
        error: The exception that occurred
        include_traceback: Whether to include full traceback
        **context: Additional context information

    Example:
        log_request_error(
            "get_alerts",
            error,
            include_traceback=True,
            tenant_id="tenant123"
        )
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        error_msg = f"{operation_name} 失败 | {context_str} | error={str(error)}"
    else:
        error_msg = f"{operation_name} 失败 | error={str(error)}"

    if include_traceback:
        logger.error(error_msg, exc_info=True)
    else:
        logger.error(error_msg)


def log_cache_hit(operation_name: str, cache_key: str, **extra) -> None:
    """
    Log a cache hit event.

    This function reduces duplication of cache hit logging patterns.

    Args:
        operation_name: Name of the operation
        cache_key: Cache key that was hit
        **extra: Additional information to log

    Example:
        log_cache_hit("get_alerts", "alerts_tenant123_limit20")
    """
    logger.debug(f"{operation_name} 命中缓存 | key={cache_key}")
    if extra:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
        logger.debug(f"{operation_name} 缓存详情 | {extra_str}")


def log_cache_miss(operation_name: str, cache_key: str, **extra) -> None:
    """
    Log a cache miss event.

    This function reduces duplication of cache miss logging patterns.

    Args:
        operation_name: Name of the operation
        cache_key: Cache key that was missed
        **extra: Additional information to log

    Example:
        log_cache_miss("get_alerts", "alerts_tenant123_limit20")
    """
    logger.debug(f"{operation_name} 未命中缓存 | key={cache_key}")
    if extra:
        extra_str = " | ".join(f"{k}={v}" for k, v in extra.items())
        logger.debug(f"{operation_name} 缓存详情 | {extra_str}")


def log_operation_start(operation_name: str, **params) -> None:
    """
    Log the start of an operation.

    This function reduces duplication of operation start logging patterns.

    Args:
        operation_name: Name of the operation
        **params: Operation parameters to log

    Example:
        log_operation_start("collect_metrics", host="server01", metrics=["cpu", "memory"])
    """
    param_str = " | ".join(f"{k}={v}" for k, v in params.items())
    logger.info(f"开始 {operation_name} | {param_str}")


def log_operation_complete(
    operation_name: str, duration_ms: Optional[float] = None, **result_info
) -> None:
    """
    Log the completion of an operation.

    This function reduces duplication of operation completion logging patterns.

    Args:
        operation_name: Name of the operation
        duration_ms: Duration in milliseconds
        **result_info: Result information to log

    Example:
        log_operation_complete(
            "collect_metrics",
            duration_ms=1250.5,
            metrics_count=10
        )
    """
    if duration_ms is not None:
        logger.info(f"{operation_name} 完成 | 耗时={duration_ms:.2f}ms")
    else:
        logger.info(f"{operation_name} 完成")

    if result_info:
        result_str = " | ".join(f"{k}={v}" for k, v in result_info.items())
        logger.debug(f"{operation_name} 结果 | {result_str}")


def log_warning(operation_name: str, message: str, **context) -> None:
    """
    Log a warning message with operation context.

    This function reduces duplication of warning logging patterns.

    Args:
        operation_name: Name of the operation
        message: Warning message
        **context: Additional context

    Example:
        log_warning(
            "get_alerts",
            "Rate limit approaching",
            current_rate=95,
            limit=100
        )
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        logger.warning(f"{operation_name} 警告 | {message} | {context_str}")
    else:
        logger.warning(f"{operation_name} 警告 | {message}")


def log_security_event(
    event_type: str, description: str, request: Optional[Request] = None, **details
) -> None:
    """
    Log a security-related event.

    This function reduces duplication of security event logging patterns.

    Args:
        event_type: Type of security event (e.g., "AUTH_FAILURE", "UNAUTHORIZED_ACCESS")
        description: Description of the event
        request: FastAPI request object
        **details: Additional details

    Example:
        log_security_event(
            "AUTH_FAILURE",
            "Invalid token provided",
            request,
            user_id="user123"
        )
    """
    client_ip = request.client.host if request and request.client else "unknown"
    detail_str = " | ".join(f"{k}={v}" for k, v in details.items())
    logger.warning(
        f"安全事件 | type={event_type} | description={description} | "
        f"client={client_ip} | {detail_str}"
    )


def format_log_params(**params) -> str:
    """
    Format parameters for logging in a consistent way.

    This function reduces duplication of parameter formatting logic.

    Args:
        **params: Parameters to format

    Returns:
        Formatted parameter string

    Example:
        params_str = format_log_params(limit=20, offset=0, filter="active")
        # Returns: "limit=20 | offset=0 | filter=active"
    """
    return " | ".join(f"{k}={v}" for k, v in params.items())


class OperationLogger:
    """
    Context manager for logging operation lifecycle.

    This class provides a convenient way to log the start and end
    of operations with consistent formatting.

    Example:
        with OperationLogger("collect_metrics", host="server01") as op_log:
            result = perform_collection()
            op_log.log_success(metrics_count=len(result))
    """

    def __init__(self, operation_name: str, **params):
        """
        Initialize the operation logger.

        Args:
            operation_name: Name of the operation
            **params: Operation parameters
        """
        self.operation_name = operation_name
        self.params = params
        self.start_time = None

    def __enter__(self):
        """Log operation start and record start time."""
        import time

        self.start_time = time.time()
        log_operation_start(self.operation_name, **self.params)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Log operation completion or error."""
        import time

        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else None

        if exc_type is not None:
            log_request_error(
                self.operation_name, exc_val, include_traceback=True, duration_ms=duration_ms
            )
        else:
            log_operation_complete(self.operation_name, duration_ms=duration_ms)

        return False  # Don't suppress exceptions

    def log_success(self, **result_info):
        """
        Log operation success with additional result information.

        Args:
            **result_info: Result information to log
        """
        log_request_success(self.operation_name, result_info=result_info)

    def log_warning(self, message: str, **context):
        """
        Log a warning during the operation.

        Args:
            message: Warning message
            **context: Additional context
        """
        log_warning(self.operation_name, message, **context)
