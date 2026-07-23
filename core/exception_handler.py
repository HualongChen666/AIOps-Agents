# -*- coding: utf-8 -*-
"""
Unified Exception Handling Module
统一异常处理模块

Provides centralized exception handling for the AIOps Agent system.
Includes custom exception classes and error response formatting.
"""

import logging
import traceback
from typing import Any, Dict, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

from core.api_response_standard import ErrorCode, create_error_response

logger = logging.getLogger(__name__)


class AIOpsException(Exception):
    """Base exception class for AIOps Agent"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class DatabaseException(AIOpsException):
    """Database-related exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.DATABASE_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class AIException(AIOpsException):
    """AI engine-related exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.AI_ANALYSIS_FAILED,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ValidationException(AIOpsException):
    """Input validation exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.VALIDATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class AuthenticationException(AIOpsException):
    """Authentication-related exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.AUTHENTICATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_401_UNAUTHORIZED,
            details=details,
        )


class AuthorizationException(AIOpsException):
    """Authorization-related exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.AUTHORIZATION_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_403_FORBIDDEN,
            details=details,
        )


class ResourceNotFoundException(AIOpsException):
    """Resource not found exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.RESOURCE_NOT_FOUND,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ConfigurationException(AIOpsException):
    """Configuration-related exceptions"""

    def __init__(
        self,
        message: str,
        error_code: str = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


async def aiops_exception_handler(request: Request, exc: AIOpsException) -> JSONResponse:
    """
    Unified exception handler for AIOps exceptions (使用统一响应格式)

    Args:
        request: FastAPI request object
        exc: AIOps exception

    Returns:
        JSON response with error details
    """
    logger.error(
        f"AIOps Exception: {exc.error_code} - {exc.message}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "details": exc.details,
            "path": request.url.path,
            "method": request.method,
        },
    )

    # 使用统一响应格式
    error_response = create_error_response(
        error=exc.message, error_code=exc.error_code, message=exc.message
    )

    return JSONResponse(status_code=exc.status_code, content=error_response)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Generic exception handler for unexpected errors (使用统一响应格式)

    Args:
        request: FastAPI request object
        exc: Generic exception

    Returns:
        JSON response with error details
    """
    logger.error(
        f"Unhandled Exception: {type(exc).__name__} - {str(exc)}",
        extra={
            "exception_type": type(exc).__name__,
            "path": request.url.path,
            "method": request.method,
            "traceback": traceback.format_exc(),
        },
    )

    # 使用统一响应格式
    error_response = create_error_response(
        error="An unexpected error occurred",
        error_code=ErrorCode.INTERNAL_ERROR,
        message=f"{type(exc).__name__}: {str(exc)}",
    )

    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error_response)


def setup_exception_handlers(app):
    """
    Setup exception handlers for FastAPI application

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AIOpsException, aiops_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
