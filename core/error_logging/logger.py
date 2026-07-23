# -*- coding: utf-8 -*-
"""
结构化日志记录器模块

提供结构化的错误日志记录功能。
"""

import json
from datetime import datetime
from typing import Any, Dict, Optional

from loguru import logger


class StructuredErrorLogger:
    """
    结构化错误日志记录器

    使用loguru提供结构化的错误日志记录，支持JSON格式输出。
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        初始化结构化错误日志记录器

        Args:
            log_file: 日志文件路径
        """
        self.log_file = log_file
        self._configure_logger()

    def _configure_logger(self):
        """配置日志记录器"""
        if self.log_file:
            logger.add(
                self.log_file,
                rotation="10 MB",
                retention="30 days",
                level="ERROR",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                serialize=True,
                compression="zip",
                enqueue=True,
            )
        else:
            # 默认日志文件
            logger.add(
                "logs/error_{time:YYYY-MM-DD}.log",
                rotation="10 MB",
                retention="30 days",
                level="ERROR",
                format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
                serialize=True,
                compression="zip",
                enqueue=True,
            )

    def log_error(
        self,
        error_code: str,
        message: str,
        severity: str = "error",
        category: str = "business",
        context: Optional[Dict[str, Any]] = None,
        error_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        """
        记录错误日志

        Args:
            error_code: 错误码
            message: 错误消息
            severity: 严重程度
            category: 错误分类
            context: 上下文信息
            error_id: 错误ID
            stack_trace: 堆栈追踪
        """
        log_data = {
            "error_code": error_code,
            "message": message,
            "severity": severity,
            "category": category,
            "timestamp": datetime.now().isoformat(),
        }

        if error_id:
            log_data["error_id"] = error_id

        if context:
            log_data["context"] = context  # type: ignore[assignment]

        if stack_trace:
            log_data["stack_trace"] = stack_trace

        # 根据严重程度选择日志级别
        if severity == "debug":
            logger.debug(json.dumps(log_data, ensure_ascii=False))
        elif severity == "info":
            logger.info(json.dumps(log_data, ensure_ascii=False))
        elif severity == "warning":
            logger.warning(json.dumps(log_data, ensure_ascii=False))
        elif severity == "error":
            logger.error(json.dumps(log_data, ensure_ascii=False))
        elif severity == "critical":
            logger.critical(json.dumps(log_data, ensure_ascii=False))
        elif severity == "fatal":
            logger.critical(json.dumps(log_data, ensure_ascii=False))
        else:
            logger.error(json.dumps(log_data, ensure_ascii=False))

    def log_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None):
        """
        记录异常日志

        Args:
            exception: 异常对象
            context: 上下文信息
        """
        from core.exceptions import AIOpsBaseException

        if isinstance(exception, AIOpsBaseException):
            self.log_error(
                error_code=exception.error_code,
                message=exception.message,
                severity=exception.severity.value,
                category=exception.category.value,
                context=exception.context,
                error_id=exception.error_id,
                stack_trace=exception.stack_trace,
            )
        else:
            self.log_error(
                error_code="01_15_0003",
                message=str(exception),
                severity="error",
                category="system",
                context=context,
                stack_trace=exception.__traceback__,  # type: ignore[arg-type]
            )


# 全局结构化错误日志记录器实例
_structured_error_logger = StructuredErrorLogger()


def log_error(
    error_code: str,
    message: str,
    severity: str = "error",
    category: str = "business",
    context: Optional[Dict[str, Any]] = None,
    error_id: Optional[str] = None,
    stack_trace: Optional[str] = None,
):
    """
    记录错误日志（便捷函数）

    Args:
        error_code: 错误码
        message: 错误消息
        severity: 严重程度
        category: 错误分类
        context: 上下文信息
        error_id: 错误ID
        stack_trace: 堆栈追踪
    """
    _structured_error_logger.log_error(
        error_code=error_code,
        message=message,
        severity=severity,
        category=category,
        context=context,
        error_id=error_id,
        stack_trace=stack_trace,
    )


def log_exception(exception: Exception, context: Optional[Dict[str, Any]] = None):
    """
    记录异常日志（便捷函数）

    Args:
        exception: 异常对象
        context: 上下文信息
    """
    _structured_error_logger.log_exception(exception, context)


def get_structured_error_logger() -> StructuredErrorLogger:
    """
    获取结构化错误日志记录器实例

    Returns:
        结构化错误日志记录器实例
    """
    return _structured_error_logger
