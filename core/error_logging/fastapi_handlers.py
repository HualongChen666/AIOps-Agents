# -*- coding: utf-8 -*-
"""
FastAPI异常处理器模块

提供FastAPI的异常处理器，将自定义异常转换为HTTP响应。
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_409_CONFLICT,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_502_BAD_GATEWAY,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from core.exceptions import (
    AIModelException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    ExternalServiceException,
    NetworkException,
    PermissionDeniedException,
    QuotaExceededException,
    ResourceNotFoundException,
    SystemFatalException,
    ValidationException,
    VersionMismatchException,
)


async def validation_exception_handler(request: Request, exc: ValidationException) -> JSONResponse:
    """
    验证异常处理器

    Args:
        request: 请求对象
        exc: 验证异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_400_BAD_REQUEST,
        content={
            "error_code": exc.error_code,
            "error_type": "ValidationException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def resource_not_found_exception_handler(
    request: Request, exc: ResourceNotFoundException
) -> JSONResponse:
    """
    资源未找到异常处理器

    Args:
        request: 请求对象
        exc: 资源未找到异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_404_NOT_FOUND,
        content={
            "error_code": exc.error_code,
            "error_type": "ResourceNotFoundException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def authentication_exception_handler(
    request: Request, exc: AuthenticationException
) -> JSONResponse:
    """
    认证异常处理器

    Args:
        request: 请求对象
        exc: 认证异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_401_UNAUTHORIZED,
        content={
            "error_code": exc.error_code,
            "error_type": "AuthenticationException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def authorization_exception_handler(
    request: Request, exc: AuthorizationException
) -> JSONResponse:
    """
    授权异常处理器

    Args:
        request: 请求对象
        exc: 授权异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_403_FORBIDDEN,
        content={
            "error_code": exc.error_code,
            "error_type": "AuthorizationException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def permission_denied_exception_handler(
    request: Request, exc: PermissionDeniedException
) -> JSONResponse:
    """
    权限拒绝异常处理器

    Args:
        request: 请求对象
        exc: 权限拒绝异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_403_FORBIDDEN,
        content={
            "error_code": exc.error_code,
            "error_type": "PermissionDeniedException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def database_exception_handler(request: Request, exc: DatabaseException) -> JSONResponse:
    """
    数据库异常处理器

    Args:
        request: 请求对象
        exc: 数据库异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": exc.error_code,
            "error_type": "DatabaseException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def network_exception_handler(request: Request, exc: NetworkException) -> JSONResponse:
    """
    网络异常处理器

    Args:
        request: 请求对象
        exc: 网络异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_502_BAD_GATEWAY,
        content={
            "error_code": exc.error_code,
            "error_type": "NetworkException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def external_service_exception_handler(
    request: Request, exc: ExternalServiceException
) -> JSONResponse:
    """
    外部服务异常处理器

    Args:
        request: 请求对象
        exc: 外部服务异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_502_BAD_GATEWAY,
        content={
            "error_code": exc.error_code,
            "error_type": "ExternalServiceException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def ai_model_exception_handler(request: Request, exc: AIModelException) -> JSONResponse:
    """
    AI模型异常处理器

    Args:
        request: 请求对象
        exc: AI模型异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": exc.error_code,
            "error_type": "AIModelException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def quota_exceeded_exception_handler(
    request: Request, exc: QuotaExceededException
) -> JSONResponse:
    """
    配额超限异常处理器

    Args:
        request: 请求对象
        exc: 配额超限异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_429_TOO_MANY_REQUESTS,
        content={
            "error_code": exc.error_code,
            "error_type": "QuotaExceededException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def version_mismatch_exception_handler(
    request: Request, exc: VersionMismatchException
) -> JSONResponse:
    """
    版本不匹配异常处理器

    Args:
        request: 请求对象
        exc: 版本不匹配异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_409_CONFLICT,
        content={
            "error_code": exc.error_code,
            "error_type": "VersionMismatchException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def system_fatal_exception_handler(
    request: Request, exc: SystemFatalException
) -> JSONResponse:
    """
    系统致命异常处理器

    Args:
        request: 请求对象
        exc: 系统致命异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "error_code": exc.error_code,
            "error_type": "SystemFatalException",
            "message": exc.message,
            "error_id": exc.error_id,
            "timestamp": exc.timestamp.isoformat() if exc.timestamp else None,
            "context": exc.context,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    通用异常处理器

    Args:
        request: 请求对象
        exc: 异常

    Returns:
        JSON响应
    """
    from core.error_logging.logger import log_exception

    log_exception(exc)
    return JSONResponse(
        status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "01_15_0003",
            "error_type": "InternalServerError",
            "message": "内部服务器错误",
            "error_id": "unknown",
            "timestamp": "unknown",
            "context": {"detail": str(exc)},
        },
    )


def setup_exception_handlers(app):
    """
    设置FastAPI异常处理器

    Args:
        app: FastAPI应用实例
    """
    app.add_exception_handler(ValidationException, validation_exception_handler)
    app.add_exception_handler(ResourceNotFoundException, resource_not_found_exception_handler)
    app.add_exception_handler(AuthenticationException, authentication_exception_handler)
    app.add_exception_handler(AuthorizationException, authorization_exception_handler)
    app.add_exception_handler(PermissionDeniedException, permission_denied_exception_handler)
    app.add_exception_handler(DatabaseException, database_exception_handler)
    app.add_exception_handler(NetworkException, network_exception_handler)
    app.add_exception_handler(ExternalServiceException, external_service_exception_handler)
    app.add_exception_handler(AIModelException, ai_model_exception_handler)
    app.add_exception_handler(QuotaExceededException, quota_exceeded_exception_handler)
    app.add_exception_handler(VersionMismatchException, version_mismatch_exception_handler)
    app.add_exception_handler(SystemFatalException, system_fatal_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)
