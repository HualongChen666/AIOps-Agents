# -*- coding: utf-8 -*-
"""
安全异常类模块

定义安全相关的异常类。
"""

from typing import Any, Dict, Optional

from .base import AIOpsBaseException, ErrorCategory, ErrorSeverity


class SecurityException(AIOpsBaseException):
    """
    安全异常基类

    所有安全相关异常的基类。
    """

    def __init__(
        self,
        message: str,
        error_code: str = "02_01_0001",
        severity: ErrorSeverity = ErrorSeverity.WARNING,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            severity=severity,
            category=ErrorCategory.SECURITY,
            context=context,
            original_exception=original_exception,
        )


class AuthenticationException(SecurityException):
    """
    认证异常

    认证失败时抛出。

    HTTP状态码: 401
    错误码: 02_01_0001
    """

    def __init__(
        self,
        message: str,
        token: Optional[str] = None,
        expired_at: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化认证异常

        Args:
            message: 错误消息
            token: Token（脱敏）
            expired_at: 过期时间
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if token is not None:
            # 脱敏处理：只显示前8位和后4位
            if len(token) > 12:
                masked_value = f"{token[:8]}...{token[-4:]}"
            else:
                masked_value = "***"
            error_context["token"] = masked_value
        if expired_at is not None:
            error_context["expired_at"] = expired_at

        super().__init__(
            message=message,
            error_code="02_01_0001",
            context=error_context,
            original_exception=original_exception,
        )
        self.token = token
        self.expired_at = expired_at


class AuthorizationException(SecurityException):
    """
    授权异常

    授权失败时抛出。

    HTTP状态码: 403
    错误码: 02_03_0001
    """

    def __init__(
        self,
        message: str,
        required_role: Optional[str] = None,
        current_role: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化授权异常

        Args:
            message: 错误消息
            required_role: 需要的角色
            current_role: 当前角色
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if required_role is not None:
            error_context["required_role"] = required_role
        if current_role is not None:
            error_context["current_role"] = current_role

        super().__init__(
            message=message,
            error_code="02_03_0001",
            severity=ErrorSeverity.ERROR,
            context=error_context,
            original_exception=original_exception,
        )
        self.required_role = required_role
        self.current_role = current_role


class PermissionDeniedException(SecurityException):
    """
    权限拒绝异常

    权限不足时抛出。

    HTTP状态码: 403
    错误码: 02_03_0002
    """

    def __init__(
        self,
        message: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化权限拒绝异常

        Args:
            message: 错误消息
            resource: 资源标识
            action: 操作类型
            context: 上下文信息
            original_exception: 原始异常
        """
        error_context = context or {}
        if resource is not None:
            error_context["resource"] = resource
        if action is not None:
            error_context["action"] = action

        super().__init__(
            message=message,
            error_code="02_03_0002",
            severity=ErrorSeverity.ERROR,
            context=error_context,
            original_exception=original_exception,
        )
        self.resource = resource
        self.action = action
