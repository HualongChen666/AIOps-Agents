# -*- coding: utf-8 -*-
"""
业务异常类模块

定义业务逻辑相关的异常类。
"""

from typing import Any, Dict, Optional

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity


class BusinessException(AIOpsBaseException):
    """
    业务异常基类

    所有业务逻辑相关异常的基类。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "01_04_0001",
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.BUSINESS,
            context=context,
            original_exception=original_exception,
        )


class ValidationException(BusinessException):
    """
    验证异常

    输入验证失败时抛出。

    HTTP状态码: 400
    错误码: 01_01_0001
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化验证异常

        Args:
            message: 错误消息
            field: 验证失败的字段名
            value: 验证失败的值
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if field is not None:
            error_context["field"] = field
        if value is not None:
            error_context["value"] = value

        super().__init__(
            message=message,
            error_code="01_01_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.field = field
        self.value = value
        # 覆盖严重程度为WARNING
        self.severity = ErrorSeverity.WARNING


class ResourceNotFoundException(BusinessException):
    """
    资源未找到异常

    资源不存在时抛出。

    HTTP状态码: 404
    错误码: 01_02_0001
    """

    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[Any] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化资源未找到异常

        Args:
            message: 错误消息
            resource_type: 资源类型
            resource_id: 资源ID
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if resource_type is not None:
            error_context["resource_type"] = resource_type
        if resource_id is not None:
            error_context["resource_id"] = str(resource_id)

        super().__init__(
            message=message,
            error_code="01_02_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.resource_type = resource_type
        self.resource_id = resource_id


class BusinessLogicException(BusinessException):
    """
    业务逻辑异常

    业务规则违反时抛出。

    HTTP状态码: 422
    错误码: 01_04_0001
    """

    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化业务逻辑异常

        Args:
            message: 错误消息
            operation: 操作名称
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if operation is not None:
            error_context["operation"] = operation

        super().__init__(
            message=message,
            error_code="01_04_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.operation = operation


class StateInvalidException(BusinessException):
    """
    状态无效异常

    对象状态不允许操作时抛出。

    HTTP状态码: 422
    错误码: 01_05_0001
    """

    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        required_state: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化状态无效异常

        Args:
            message: 错误消息
            current_state: 当前状态
            required_state: 需要的状态
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if current_state is not None:
            error_context["current_state"] = current_state
        if required_state is not None:
            error_context["required_state"] = required_state

        super().__init__(
            message=message,
            error_code="01_05_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.current_state = current_state
        self.required_state = required_state


class WorkflowException(BusinessException):
    """
    工作流异常

    工作流执行失败时抛出。

    HTTP状态码: 422
    错误码: 13_04_0001
    """

    def __init__(
        self,
        message: str,
        workflow_id: Optional[str] = None,
        step: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化工作流异常

        Args:
            message: 错误消息
            workflow_id: 工作流ID
            step: 失败的步骤
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if workflow_id is not None:
            error_context["workflow_id"] = workflow_id
        if step is not None:
            error_context["step"] = step

        super().__init__(
            message=message,
            error_code="13_04_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.workflow_id = workflow_id
        self.step = step


class QuotaExceededException(BusinessException):
    """
    配额超限异常

    资源配额超限时抛出。

    HTTP状态码: 429
    错误码: 18_06_0003
    """

    def __init__(
        self,
        message: str,
        quota_type: Optional[str] = None,
        current_usage: Optional[float] = None,
        quota_limit: Optional[float] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化配额超限异常

        Args:
            message: 错误消息
            quota_type: 配额类型
            current_usage: 当前使用量
            quota_limit: 配额限制
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if quota_type is not None:
            error_context["quota_type"] = quota_type
        if current_usage is not None:
            error_context["current_usage"] = current_usage
        if quota_limit is not None:
            error_context["quota_limit"] = quota_limit

        super().__init__(
            message=message,
            error_code="18_06_0003",
            context=error_context,
            original_exception=original_exception,
        )
        self.quota_type = quota_type
        self.current_usage = current_usage
        self.quota_limit = quota_limit
