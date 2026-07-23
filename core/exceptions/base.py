# -*- coding: utf-8 -*-
"""
基础异常类模块

定义AIOps系统的基础异常类，所有自定义异常的基类。
"""

import json
import traceback
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(Enum):
    """错误严重程度"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """错误分类"""

    BUSINESS = "business"
    SYSTEM = "system"
    SECURITY = "security"
    THIRD_PARTY = "third_party"
    CRITICAL = "critical"


class AIOpsBaseException(Exception):
    """
    AIOps系统基础异常类

    所有自定义异常的基类，提供统一的异常处理接口。

    Attributes:
        message: 错误消息
        error_code: 错误码
        severity: 严重程度
        category: 错误分类
        context: 上下文信息
        error_id: 错误唯一标识
        timestamp: 发生时间
        stack_trace: 堆栈追踪
        original_exception: 原始异常
    """

    def __init__(
        self,
        message: str,
        error_code: str = "01_15_0001",
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.BUSINESS,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        """
        初始化基础异常

        Args:
            message: 错误消息
            error_code: 错误码
            severity: 严重程度
            category: 错误分类
            context: 上下文信息
            original_exception: 原始异常
        """
        self.message = message
        self.error_code = error_code
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.original_exception = original_exception
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        self.stack_trace = traceback.format_exc() if original_exception else None

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式

        Returns:
            包含异常所有信息的字典
        """
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "stack_trace": self.stack_trace,
        }

    def to_json(self) -> str:
        """
        转换为JSON格式

        Returns:
            JSON格式的异常信息
        """
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def with_context(self, **kwargs) -> "AIOpsBaseException":
        """
        添加上下文信息

        Args:
            **kwargs: 上下文键值对

        Returns:
            自身，支持链式调用
        """
        self.context.update(kwargs)
        return self

    def __str__(self) -> str:
        """字符串表示"""
        return f"[{self.error_code}] {self.message}"

    def __repr__(self) -> str:
        """对象表示"""
        return f"{self.__class__.__name__}(error_code={self.error_code}, message={self.message})"
