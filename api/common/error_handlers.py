# -*- coding: utf-8 -*-
"""
Common Error Handlers and Response Helpers
===========================================

Provides reusable error handling and response formatting functions
to reduce code duplication across API routers.

This module addresses the following code duplication issues:
- Repeated HTTPException raising patterns
- Repeated error logging patterns
- Repeated response formatting patterns
- Repeated error message truncation
"""

import logging
from typing import Any, Optional

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def handle_service_error(
    error: Exception,
    operation_name: str,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    detail_prefix: str = "",
    max_detail_length: int = 200,
    log_exception: bool = True,
) -> None:
    """
    Handle service errors with consistent logging and HTTP exception raising.

    This function reduces duplication of error handling patterns across routers.

    Args:
        error: The exception that occurred
        operation_name: Name of the operation that failed (for logging)
        status_code: HTTP status code to raise (default: 500)
        detail_prefix: Prefix for the error detail message
        max_detail_length: Maximum length of error detail message
        log_exception: Whether to log the full exception with traceback

    Raises:
        HTTPException: With the specified status code and formatted detail

    Example:
        try:
            result = some_operation()
        except Exception as e:
            handle_service_error(e, "some_operation", status_code=400)
    """
    if log_exception:
        logger.error(f"{operation_name} failed: {error}", exc_info=True)
    else:
        logger.error(f"{operation_name} failed: {error}")

    error_detail = str(error)
    if detail_prefix:
        error_detail = f"{detail_prefix}: {error_detail}"

    # Truncate error detail to prevent excessively long responses
    if len(error_detail) > max_detail_length:
        error_detail = error_detail[:max_detail_length]

    raise HTTPException(status_code=status_code, detail=error_detail)


def create_success_response(
    data: Any = None, message: str = "success", status: str = "ok", **extra_fields
) -> dict[str, Any]:
    """
    Create a standardized success response.

    This function reduces duplication of response formatting patterns.

    Args:
        data: The main data to include in the response
        message: Success message
        status: Status indicator
        **extra_fields: Additional fields to include in the response

    Returns:
        Formatted success response dictionary

    Example:
        return create_success_response(
            data={"id": 123},
            message="Operation completed successfully"
        )
    """
    response: dict[str, Any] = {"status": status, "message": message}
    if data is not None:
        response["data"] = data
    response.update(extra_fields)
    return response


def create_list_response(
    items: list[Any], total: Optional[int] = None, **extra_fields
) -> dict[str, Any]:
    """
    Create a standardized list response.

    This function reduces duplication of list response formatting patterns.

    Args:
        items: List of items to return
        total: Total count (if different from len(items))
        **extra_fields: Additional fields to include in the response

    Returns:
        Formatted list response dictionary

    Example:
        return create_list_response(
            items=users,
            total=len(users),
            page=1
        )
    """
    if total is None:
        total = len(items)
    response: dict[str, Any] = {"total": total, "items": items}
    response.update(extra_fields)
    return response


def create_error_response(
    error_message: str,
    error_code: Optional[str] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    **extra_fields,
) -> dict[str, Any]:
    """
    Create a standardized error response.

    This function reduces duplication of error response formatting patterns.

    Args:
        error_message: Error message
        error_code: Optional error code for programmatic handling
        status_code: HTTP status code
        **extra_fields: Additional fields to include in the response

    Returns:
        Formatted error response dictionary

    Example:
        return create_error_response(
            error_message="Resource not found",
            error_code="NOT_FOUND",
            status_code=404
        )
    """
    response: dict[str, Any] = {
        "success": False,
        "error": error_message,
        "status_code": status_code,
    }
    if error_code:
        response["error_code"] = error_code
    response.update(extra_fields)
    return response


def validate_and_raise_422(
    condition: bool, field_name: str, error_message: str = "Validation failed"
) -> None:
    """
    Validate a condition and raise 422 if it fails.

    This function reduces duplication of validation error patterns.

    Args:
        condition: Condition to validate
        field_name: Name of the field being validated
        error_message: Error message to use

    Raises:
        HTTPException: With status 422 if validation fails

    Example:
        validate_and_raise_422(limit > 0, "limit", "limit must be positive")
    """
    if not condition:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{error_message}: {field_name}",
        )


def check_feature_availability(
    feature_available: bool,
    feature_name: str,
    status_code: int = status.HTTP_503_SERVICE_UNAVAILABLE,
) -> None:
    """
    Check if a feature is available and raise an exception if not.

    This function reduces duplication of feature availability checks.

    Args:
        feature_available: Whether the feature is available
        feature_name: Name of the feature
        status_code: HTTP status code to raise (default: 503)

    Raises:
        HTTPException: If feature is not available

    Example:
        check_feature_availability(ALERT_INTELLIGENCE_AVAILABLE, "Alert Intelligence")
    """
    if not feature_available:
        raise HTTPException(status_code=status_code, detail=f"{feature_name} is not available")


def get_client_ip(request: Request) -> str:
    """
    Safely extract client IP from request.

    This function reduces duplication of client IP extraction logic.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address or "unknown" if not available

    Example:
        operator_ip = get_client_ip(request)
    """
    return request.client.host if request.client else "unknown"


def create_timestamp_response(data: Any, timestamp_field: str = "timestamp") -> dict[str, Any]:
    """
    Create a response with an ISO format timestamp.

    This function reduces duplication of timestamped response patterns.

    Args:
        data: The main data to include
        timestamp_field: Field name for the timestamp

    Returns:
        Response dictionary with timestamp

    Example:
        from datetime import datetime, timezone
        return create_timestamp_response({"status": "alive"})
    """
    from datetime import datetime, timezone

    response: dict[str, Any] = data if isinstance(data, dict) else {"data": data}
    response[timestamp_field] = datetime.now(timezone.utc).isoformat()
    return response
