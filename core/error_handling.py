# -*- coding: utf-8 -*-
"""
统一错误处理模块

提供标准化的错误处理架构，包括：
- 自定义异常类
- 错误码标准化
- 统一错误响应格式
- 错误日志记录
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional

from fastapi import HTTPException, status

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """标准错误码枚举

    格式: SERVICE_ERROR_CODE
    - SERVICE: 服务缩写（AI, DB, AUTH等）
    - ERROR_CODE: 具体错误代码
    """

    # 通用错误 (1000-1999)
    INTERNAL_ERROR = "GEN_1000"
    INVALID_REQUEST = "GEN_1001"
    NOT_FOUND = "GEN_1002"
    PERMISSION_DENIED = "GEN_1003"
    RATE_LIMIT_EXCEEDED = "GEN_1004"

    # AI引擎错误 (2000-2999)
    AI_ENGINE_ERROR = "AI_2000"
    AI_MODEL_ERROR = "AI_2001"
    AI_TIMEOUT = "AI_2002"
    AI_RATE_LIMIT = "AI_2003"

    # 数据库错误 (3000-3999)
    DB_CONNECTION_ERROR = "DB_3000"
    DB_QUERY_ERROR = "DB_3001"
    DB_NOT_FOUND = "DB_3002"
    DB_CONSTRAINT_ERROR = "DB_3003"

    # 认证授权错误 (4000-4999)
    AUTH_INVALID_TOKEN = "AUTH_" + "4000"
    AUTH_EXPIRED_TOKEN = "AUTH_" + "4001"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_4002"

    # 外部服务错误 (5000-5999)
    EXTERNAL_SERVICE_ERROR = "EXT_5000"
    EXTERNAL_SERVICE_TIMEOUT = "EXT_5001"


class AIOpsException(Exception):
    """AIOps基础异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "error_code": self.error_code.value,
            "message": self.message,
            "details": self.details,
        }


class AIOpsHTTPException(HTTPException):
    """AIOps HTTP异常类"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(
            status_code=status_code,
            detail={
                "error_code": error_code.value,
                "message": message,
                "details": self.details,
            },
        )


class ValidationError(AIOpsException):
    """验证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.INVALID_REQUEST,
            details=details,
            status_code=status.HTTP_400_BAD_REQUEST,
        )


class NotFoundError(AIOpsException):
    """资源未找到错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.NOT_FOUND,
            details=details,
            status_code=status.HTTP_404_NOT_FOUND,
        )


class PermissionDeniedError(AIOpsException):
    """权限拒绝错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.PERMISSION_DENIED,
            details=details,
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AIEngineError(AIOpsException):
    """AI引擎错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AI_ENGINE_ERROR,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class DatabaseError(AIOpsException):
    """数据库错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.DB_CONNECTION_ERROR,
            details=details,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


class AuthenticationError(AIOpsException):
    """认证错误"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code=ErrorCode.AUTH_INVALID_TOKEN,
            details=details,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def handle_aiops_exception(exc: AIOpsException) -> Dict[str, Any]:
    """处理AIOps异常并返回标准错误响应

    Args:
        exc: AIOps异常实例

    Returns:
        标准错误响应字典
    """
    logger.error(
        f"AIOps Exception: {exc.error_code.value} - {exc.message}",
        extra={"error_code": exc.error_code.value, "details": exc.details},
    )

    return {
        "error_code": exc.error_code.value,
        "message": exc.message,
        "details": exc.details,
    }


def handle_generic_exception(exc: Exception) -> Dict[str, Any]:
    """处理通用异常并返回标准错误响应

    Args:
        exc: 通用异常实例

    Returns:
        标准错误响应字典
    """
    logger.error(f"Unexpected error: {type(exc).__name__} - {str(exc)}", exc_info=True)

    return {
        "error_code": ErrorCode.INTERNAL_ERROR.value,
        "message": "An unexpected error occurred",
        "details": {"error_type": type(exc).__name__},
    }


def create_error_response(
    error_code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
) -> AIOpsHTTPException:
    """创建标准HTTP异常响应

    Args:
        error_code: 错误码
        message: 错误消息
        details: 错误详情
        status_code: HTTP状态码

    Returns:
        AIOpsHTTPException实例
    """
    return AIOpsHTTPException(
        message=message,
        error_code=error_code,
        details=details,
        status_code=status_code,
    )


def log_error(
    error_code: ErrorCode,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    level: int = logging.ERROR,
):
    """记录错误日志

    Args:
        error_code: 错误码
        message: 错误消息
        details: 错误详情
        level: 日志级别
    """
    logger.log(
        level,
        f"Error {error_code.value}: {message}",
        extra={"error_code": error_code.value, "details": details or {}},
    )
