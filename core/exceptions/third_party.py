# -*- coding: utf-8 -*-
"""
第三方异常类模块

定义第三方服务相关的异常类。
"""

from typing import Any, Dict, Optional

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity


class ThirdPartyException(AIOpsBaseException):
    """
    第三方异常基类

    所有第三方服务相关异常的基类。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "15_06_0001",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.THIRD_PARTY,
            context=context,
            original_exception=original_exception,
        )


class ExternalServiceException(ThirdPartyException):
    """
    外部服务异常

    外部服务调用失败时抛出。

    HTTP状态码: 502
    错误码: 15_06_0001
    """

    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        service_url: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化外部服务异常

        Args:
            message: 错误消息
            service_name: 服务名称
            service_url: 服务URL
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if service_name is not None:
            error_context["service_name"] = service_name
        if service_url is not None:
            error_context["service_url"] = service_url

        super().__init__(
            message=message,
            error_code="15_06_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.service_name = service_name
        self.service_url = service_url


class AIModelException(ThirdPartyException):
    """
    AI模型异常

    AI模型相关错误时抛出。

    HTTP状态码: 500
    错误码: 11_12_0001
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        error_type: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化AI模型异常

        Args:
            message: 错误消息
            model_name: 模型名称
            error_type: 错误类型（timeout, load_failed, inference_error等）
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if model_name is not None:
            error_context["model_name"] = model_name
        if error_type is not None:
            error_context["error_type"] = error_type

        super().__init__(
            message=message,
            error_code="11_12_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.model_name = model_name
        self.error_type = error_type


class IntegrationException(ThirdPartyException):
    """
    集成异常

    集成相关错误时抛出。

    HTTP状态码: 502
    错误码: 19_06_0001
    """

    def __init__(
        self,
        message: str,
        integration_type: Optional[str] = None,
        sync_operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化集成异常

        Args:
            message: 错误消息
            integration_type: 集成类型（GitLab, Jira等）
            sync_operation: 同步操作（pull, push等）
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if integration_type is not None:
            error_context["integration_type"] = integration_type
        if sync_operation is not None:
            error_context["sync_operation"] = sync_operation

        super().__init__(
            message=message,
            error_code="19_06_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.integration_type = integration_type
        self.sync_operation = sync_operation
