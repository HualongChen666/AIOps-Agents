# -*- coding: utf-8 -*-
"""
API Helper Functions - Unified error handling and response utilities

This module provides reusable functions to eliminate duplicate code patterns
across API routes, including:
- Unified exception handling
- Standardized error responses
- Consistent logging patterns
- Decorators for automatic error handling
- Host configuration lookup
- Hostname validation
- Operator IP extraction
"""

import logging
import re
from functools import wraps
from typing import Any, Callable, Optional

from fastapi import HTTPException, Request

logger = logging.getLogger(__name__)


def handle_api_error(
    operation: str,
    error: Exception,
    status_code: int = 500,
    detail_prefix: Optional[str] = None,
    max_detail_length: int = 200,
    log_context: Optional[dict[str, Any]] = None,
) -> None:
    """
    Unified API error handling with logging and HTTPException raising.

    Args:
        operation: Name of the operation that failed (e.g., "日志采集", "通知发送")
        error: The exception that occurred
        status_code: HTTP status code to return (default: 500)
        detail_prefix: Optional prefix for the error detail message
        max_detail_length: Maximum length of error detail (default: 200)
        log_context: Optional additional context for logging

    Raises:
        HTTPException: Always raises with the specified status code and detail

    Example:
        try:
            result = some_operation()
        except Exception as e:
            handle_api_error("日志采集", e)
    """
    # Build log message
    log_msg = f"{operation}失败: {error}"
    if log_context:
        log_msg += f" | context: {log_context}"

    logger.error(log_msg, exc_info=True)

    # Build error detail
    error_detail = str(error)
    if detail_prefix:
        error_detail = f"{detail_prefix}: {error_detail}"

    # Truncate detail if too long
    if len(error_detail) > max_detail_length:
        error_detail = error_detail[:max_detail_length]

    raise HTTPException(status_code=status_code, detail=error_detail)


def validate_required_fields(
    data: dict[str, Any],
    required_fields: list[str],
    field_name: str = "data",
) -> None:
    """
    Validate that required fields are present and non-empty in a dictionary.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        field_name: Name of the data structure (for error messages)

    Raises:
        HTTPException: If validation fails with 422 status

    Example:
        validate_required_fields(alert, ["level", "title", "desc"], "alert")
    """
    if not isinstance(data, dict):
        raise HTTPException(
            status_code=422, detail=f"{field_name} 必须是 dict,收到 {type(data).__name__}"
        )

    missing = [f for f in required_fields if not data.get(f) or not str(data.get(f)).strip()]

    if missing:
        raise HTTPException(
            status_code=422, detail=f"{field_name} 缺少必填字段: {missing}(均不能为空)"
        )


def log_operation_start(
    operation: str,
    **context: Any,
) -> None:
    """
    Log the start of an operation with consistent formatting.

    Args:
        operation: Name of the operation
        **context: Additional context key-value pairs

    Example:
        log_operation_start("日志采集", host="server1", newest=10)
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        logger.info(f"{operation}开始 | {context_str}")
    else:
        logger.info(f"{operation}开始")


def log_operation_success(
    operation: str,
    **context: Any,
) -> None:
    """
    Log the successful completion of an operation.

    Args:
        operation: Name of the operation
        **context: Additional context key-value pairs

    Example:
        log_operation_success("日志采集", count=5, host="server1")
    """
    if context:
        context_str = " | ".join(f"{k}={v}" for k, v in context.items())
        logger.info(f"{operation}成功 | {context_str}")
    else:
        logger.info(f"{operation}成功")


def create_success_response(
    data: Any,
    message: Optional[str] = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Create a standardized success response.

    Args:
        data: The response data
        message: Optional success message
        **extra: Additional fields to include in response

    Returns:
        Dictionary with standardized success response format

    Example:
        return create_success_response({"logs": data}, "采集成功", total=len(data))
    """
    response = {"status": "ok"}
    if message:
        response["message"] = message
    if data is not None:
        response["data"] = data
    response.update(extra)
    return response


def create_error_response(
    message: str,
    status_code: int = 500,
    error_code: Optional[str] = None,
    **extra: Any,
) -> dict[str, Any]:
    """
    Create a standardized error response (for manual error returns).

    Note: For most cases, use handle_api_error() which raises HTTPException.
    This function is for cases where you want to return an error dict directly.

    Args:
        message: Error message
        status_code: HTTP status code
        error_code: Optional error code for programmatic handling
        **extra: Additional fields to include in response

    Returns:
        Dictionary with standardized error response format

    Example:
        return create_error_response("配置无效", 400, error_code="INVALID_CONFIG")
    """
    response = {
        "status": "error",
        "message": message,
        "status_code": status_code,
    }
    if error_code:
        response["error_code"] = error_code
    response.update(extra)
    return response


def with_error_handling(
    operation_name: Optional[str] = None,
    status_code: int = 500,
    detail_prefix: Optional[str] = None,
):
    """
    Decorator for unified error handling in API route functions.

    Automatically catches exceptions and converts them to HTTPException
    with consistent logging and error formatting.

    Args:
        operation_name: Name of the operation (defaults to function name)
        status_code: HTTP status code for errors (default: 500)
        detail_prefix: Optional prefix for error detail message

    Example:
        @with_error_handling("日志采集")
        async def collect_logs(host: str):
            # Your logic here
            return {"logs": [...]}

    The decorated function will automatically:
    - Log operation start with parameters
    - Catch any exception and log it with traceback
    - Raise HTTPException with standardized error message
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            log_operation_start(op_name, **kwargs)
            try:
                result = await func(*args, **kwargs)
                log_operation_success(op_name)
                return result
            except HTTPException:
                raise
            except Exception as e:
                handle_api_error(op_name, e, status_code, detail_prefix)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            op_name = operation_name or func.__name__
            log_operation_start(op_name, **kwargs)
            try:
                result = func(*args, **kwargs)
                log_operation_success(op_name)
                return result
            except HTTPException:
                raise
            except Exception as e:
                handle_api_error(op_name, e, status_code, detail_prefix)

        # Return appropriate wrapper based on whether function is async
        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# ============================================================
# Host Configuration & Validation Utilities
# ============================================================

# Valid hostname pattern (letters, numbers, dots, underscores, hyphens, colons)
VALID_HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._\-:]+$")


def find_host_config(
    host_name: str,
    hosts_list: list[dict[str, Any]],
    name_field: str = "name",
    host_field: str = "host",
) -> Optional[dict[str, Any]]:
    """
    Unified host configuration lookup function.

    Args:
        host_name: Host name or IP address
        hosts_list: List of host configuration dictionaries
        name_field: Field name for host name (default: "name")
        host_field: Field name for host IP (default: "host")

    Returns:
        Matching configuration dict / None

    Example:
        # Linux hosts
        find_host_config("server01", LINUX_HOSTS, "name", "host")
        # Windows hosts
        find_host_config("win01", WIN_HOSTS, "name", "ip")
    """
    if not host_name or not isinstance(host_name, str):
        return None

    cleaned = host_name.strip()
    if not cleaned or not VALID_HOSTNAME_PATTERN.match(cleaned):
        return None

    matched_host = next(
        (h for h in hosts_list if h.get(name_field) == cleaned or h.get(host_field) == cleaned),
        None,
    )
    return matched_host


def validate_hostname(host_name: str) -> str:
    """
    Hostname validation and cleaning.

    Args:
        host_name: Original hostname

    Returns:
        Cleaned hostname

    Raises:
        ValueError: If validation fails
    """
    if not host_name or not isinstance(host_name, str):
        raise ValueError("host_name 不能为空")

    cleaned = host_name.strip()
    if not cleaned:
        raise ValueError("host_name 不能为纯空白")

    if not VALID_HOSTNAME_PATTERN.match(cleaned):
        raise ValueError(f"host_name 仅允许字母数字和 '._-:', 收到: {cleaned!r}")

    return cleaned


def get_operator_ip(request: Request) -> str:
    """
    Extract operator IP from FastAPI Request.

    Args:
        request: FastAPI Request object

    Returns:
        Operator IP address, or "unknown" if unavailable
    """
    return request.client.host if request.client else "unknown"


def hostname_field_validator(v: str) -> str:
    """
    Pydantic field_validator for hostname validation.

    Usage:
        class MyModel(BaseModel):
            '''Hostname model.'''
            host_name: str
            _validate_host = field_validator("host_name")(hostname_field_validator)
    """
    return validate_hostname(v)
