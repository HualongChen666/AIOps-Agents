# -*- coding: utf-8 -*-
"""
系统异常类模块

定义系统相关的异常类。
"""

from typing import Any, Dict, Optional

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity


class SystemException(AIOpsBaseException):
    """
    系统异常基类

    所有系统相关异常的基类。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "20_15_0001",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=severity,
            category=ErrorCategory.SYSTEM,
            context=context,
            original_exception=original_exception,
        )


class DatabaseException(SystemException):
    """
    数据库异常

    数据库相关错误时抛出。

    HTTP状态码: 500
    错误码: 09_06_0001
    """

    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化数据库异常

        Args:
            message: 错误消息
            host: 数据库主机
            port: 数据库端口
            database: 数据库名称
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if host is not None:
            error_context["host"] = host
        if port is not None:
            error_context["port"] = port
        if database is not None:
            error_context["database"] = database

        super().__init__(
            message=message,
            error_code="09_06_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.host = host
        self.port = port
        self.database = database


class NetworkException(SystemException):
    """
    网络异常

    网络相关错误时抛出。

    HTTP状态码: 503
    错误码: 17_06_0001
    """

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化网络异常

        Args:
            message: 错误消息
            url: 请求URL
            timeout: 超时时间
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if url is not None:
            error_context["url"] = url
        if timeout is not None:
            error_context["timeout"] = timeout

        super().__init__(
            message=message,
            error_code="17_06_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.url = url
        self.timeout = timeout


class CacheException(SystemException):
    """
    缓存异常

    缓存相关错误时抛出。

    HTTP状态码: 500
    错误码: 10_06_0001
    """

    def __init__(
        self,
        message: str,
        cache_type: Optional[str] = None,
        key: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化缓存异常

        Args:
            message: 错误消息
            cache_type: 缓存类型（redis, memcached等）
            key: 缓存键
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if cache_type is not None:
            error_context["cache_type"] = cache_type
        if key is not None:
            error_context["key"] = key

        super().__init__(
            message=message,
            error_code="10_06_0001",
            severity=ErrorSeverity.WARNING,
            context=error_context,
            original_exception=original_exception,
        )
        self.cache_type = cache_type
        self.key = key


class ConfigurationException(SystemException):
    """
    配置异常

    配置相关错误时抛出。

    HTTP状态码: 500
    错误码: 16_14_0001
    """

    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化配置异常

        Args:
            message: 错误消息
            config_key: 配置键
            config_file: 配置文件
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if config_key is not None:
            error_context["config_key"] = config_key
        if config_file is not None:
            error_context["config_file"] = config_file

        super().__init__(
            message=message,
            error_code="16_14_0001",
            severity=ErrorSeverity.CRITICAL,
            context=error_context,
            original_exception=original_exception,
        )
        self.config_key = config_key
        self.config_file = config_file


class ResourceException(SystemException):
    """
    资源异常

    系统资源不足时抛出。

    HTTP状态码: 503
    错误码: 18_06_0001
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        available: Optional[float] = None,
        required: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化资源异常

        Args:
            message: 错误消息
            resource_type: 资源类型（memory, disk, cpu等）
            available: 可用量
            required: 需要量
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if resource_type is not None:
            error_context["resource_type"] = resource_type
        if available is not None:
            error_context["available"] = available
        if required is not None:
            error_context["required"] = required

        super().__init__(
            message=message,
            error_code="18_06_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.resource_type = resource_type
        self.available = available
        self.required = required


class VersionMismatchException(SystemException):
    """
    版本不匹配异常

    版本不兼容时抛出。

    HTTP状态码: 409
    错误码: 16_14_0002
    """

    def __init__(
        self,
        message: str,
        current_version: Optional[str] = None,
        required_version: Optional[str] = None,
        component: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化版本不匹配异常

        Args:
            message: 错误消息
            current_version: 当前版本
            required_version: 需要的版本
            component: 组件名称
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if current_version is not None:
            error_context["current_version"] = current_version
        if required_version is not None:
            error_context["required_version"] = required_version
        if component is not None:
            error_context["component"] = component

        super().__init__(
            message=message,
            error_code="16_14_0002",
            context=error_context,
            original_exception=original_exception,
        )
        self.current_version = current_version
        self.required_version = required_version
        self.component = component
