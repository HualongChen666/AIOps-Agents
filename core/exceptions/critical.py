# -*- coding: utf-8 -*-
"""
严重异常类模块

定义严重级别的异常类。
"""

from typing import Any, Dict, Optional

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity


class CriticalException(AIOpsBaseException):
    """
    严重异常基类

    所有严重级别异常的基类。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "20_15_0001",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.CRITICAL,
            context=context,
            original_exception=original_exception,
        )


class SystemFatalException(CriticalException):
    """
    系统致命异常

    系统致命错误时抛出。

    HTTP状态码: 500
    错误码: 20_15_0001
    """

    def __init__(
        self,
        message: str,
        service: Optional[str] = None,
        error_code_detail: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化系统致命异常

        Args:
            message: 错误消息
            service: 故障服务名称
            error_code_detail: 详细错误码
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if service is not None:
            error_context["service"] = service
        if error_code_detail is not None:
            error_context["error_code_detail"] = error_code_detail

        super().__init__(
            message=message,
            error_code="20_15_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.service = service
        self.error_code_detail = error_code_detail


class DataCorruptionException(CriticalException):
    """
    数据损坏异常

    数据损坏时抛出。

    HTTP状态码: 500
    错误码: 09_13_0001
    """

    def __init__(
        self,
        message: str,
        table: Optional[str] = None,
        constraint: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化数据损坏异常

        Args:
            message: 错误消息
            table: 表名
            constraint: 约束名称
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if table is not None:
            error_context["table"] = table
        if constraint is not None:
            error_context["constraint"] = constraint

        super().__init__(
            message=message,
            error_code="09_13_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.table = table
        self.constraint = constraint
