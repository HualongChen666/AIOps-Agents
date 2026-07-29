# -*- coding: utf-8 -*-
"""
Error Handling and Logging Module
错误处理和日志模块

Provides comprehensive error handling and logging capabilities:
- Unified exception handling mechanism
- Structured logging
- Error classification and grading
- Error recovery and retry mechanisms
- Error tracking and alerting
- Log aggregation and analysis
"""

import asyncio
import sys
import time
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type

from loguru import logger as loguru_logger


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

    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    SYSTEM = "system"
    EXTERNAL_SERVICE = "external_service"
    UNKNOWN = "unknown"


class LogFormat(Enum):
    """日志格式"""

    JSON = "json"
    TEXT = "text"
    STRUCTURED = "structured"


@dataclass
class ErrorRecord:
    """错误记录"""

    id: str
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: datetime
    stack_trace: str
    context: Dict[str, Any]
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    resolved: bool = False
    resolution_notes: str = ""


@dataclass
class RetryPolicy:
    """重试策略"""

    max_attempts: int = 3
    backoff_factor: float = 2.0
    initial_delay: float = 1.0
    max_delay: float = 60.0
    retry_on: List[Type[Exception]] = field(default_factory=list)


@dataclass
class LogEntry:
    """日志条目"""

    timestamp: datetime
    level: str
    message: str
    module: str
    function: str
    line: int
    context: Dict[str, Any]


@dataclass
class ErrorStatistic:
    """错误统计"""

    count: int
    last_occurrence: Optional[str] = None


class AIOpsException(Exception):
    """AIOps基础异常类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_exception = original_exception
        self.error_id = str(uuid.uuid4())
        self.timestamp = datetime.now()
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error_id": self.error_id,
            "error_type": self.__class__.__name__,
            "error_message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
        }


class NetworkException(AIOpsException):
    """网络异常"""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message, ErrorCategory.NETWORK, ErrorSeverity.ERROR, context, original_exception
        )


class DatabaseException(AIOpsException):
    """数据库异常"""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message, ErrorCategory.DATABASE, ErrorSeverity.ERROR, context, original_exception
        )


class AuthenticationException(AIOpsException):
    """认证异常"""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message,
            ErrorCategory.AUTHENTICATION,
            ErrorSeverity.WARNING,
            context,
            original_exception,
        )


class ValidationException(AIOpsException):
    """验证异常"""

    def __init__(
        self,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None,
    ):
        super().__init__(
            message, ErrorCategory.VALIDATION, ErrorSeverity.WARNING, context, original_exception
        )


class ErrorHandler:
    """错误处理器"""

    def __init__(self):
        """初始化错误处理器"""
        # 错误记录
        self.error_records: deque = deque(maxlen=10000)
        self.error_index: Dict[str, ErrorRecord] = {}

        # 错误统计
        self.error_statistics: Dict[str, ErrorStatistic] = defaultdict(
            lambda: ErrorStatistic(count=0, last_occurrence=None)
        )

        # 重试策略
        self.retry_policies: Dict[str, RetryPolicy] = {}

        # 错误处理器
        self.error_handlers: Dict[Type[Exception], Callable] = {}

        # 告警配置
        self.alert_thresholds: Dict[ErrorSeverity, int] = {
            ErrorSeverity.CRITICAL: 1,
            ErrorSeverity.ERROR: 5,
            ErrorSeverity.WARNING: 10,
        }

        # 配置
        self.enable_error_tracking = True
        self.enable_auto_retry = True
        self.max_error_records = 10000

    async def initialize(self):
        """初始化错误处理器"""
        loguru_logger.info("Initializing Error Handler")

        # 配置默认重试策略
        self.retry_policies["default"] = RetryPolicy(
            max_attempts=3, backoff_factor=2.0, initial_delay=1.0, max_delay=60.0
        )

        # 注册默认错误处理器
        await self._register_default_handlers()

        loguru_logger.info("Error Handler initialized successfully")

    async def _register_default_handlers(self):
        """注册默认错误处理器"""
        self.error_handlers[AIOpsException] = self._handle_aiops_exception
        self.error_handlers[NetworkException] = self._handle_network_exception
        self.error_handlers[DatabaseException] = self._handle_database_exception
        self.error_handlers[AuthenticationException] = self._handle_authentication_exception
        self.error_handlers[ValidationException] = self._handle_validation_exception

    async def handle_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecord:
        """处理异常"""
        # 记录错误
        error_record = await self._record_error(exception, context)

        # 查找并执行错误处理器
        handler = self._find_error_handler(exception)
        if handler:
            try:
                await handler(error_record)
            except Exception as handler_error:
                loguru_logger.error(f"Error handler failed: {handler_error}")

        # 检查是否需要告警
        await self._check_error_alert(error_record)

        return error_record

    async def _record_error(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecord:
        """记录错误"""
        # 确定错误类别和严重程度
        if isinstance(exception, AIOpsException):
            category = exception.category
            severity = exception.severity
            error_message = exception.message
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.ERROR
            error_message = str(exception)

        # 创建错误记录
        error_record = ErrorRecord(
            id=str(uuid.uuid4()),
            error_type=exception.__class__.__name__,
            error_message=error_message,
            category=category,
            severity=severity,
            timestamp=datetime.now(),
            stack_trace=traceback.format_exc(),
            context=context or {},
            user_id=context.get("user_id") if context else None,
            request_id=context.get("request_id") if context else None,
        )

        # 保存错误记录
        self.error_records.append(error_record)
        self.error_index[error_record.id] = error_record

        # 更新错误统计
        error_key = f"{category.value}_{error_record.error_type}"
        self.error_statistics[error_key].count += 1
        self.error_statistics[error_key].last_occurrence = error_record.timestamp.isoformat()

        # 记录到日志
        await self._log_error(error_record)

        return error_record

    async def _log_error(self, error_record: ErrorRecord):
        """记录错误到日志"""
        log_level = error_record.severity.value.upper()

        loguru_logger.log(
            log_level,
            f"[{error_record.error_type}] {error_record.error_message}",
            extra={
                "error_id": error_record.id,
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "context": error_record.context,
                "stack_trace": error_record.stack_trace,
            },
        )

    def _find_error_handler(self, exception: Exception) -> Optional[Callable]:
        """查找错误处理器"""
        # 查找精确匹配
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                return handler

        # 查找基类匹配
        for exc_type, handler in self.error_handlers.items():
            if isinstance(exception, exc_type):
                return handler

        return None

    async def _handle_aiops_exception(self, error_record: ErrorRecord):
        """处理AIOps异常：记录结构化日志并触发告警阈值检查。"""
        loguru_logger.log(
            error_record.severity.value.upper(),
            f"[AIOps Exception] {error_record.error_message}",
            extra={
                "error_id": error_record.id,
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "error_type": error_record.error_type,
                "context": error_record.context,
            },
        )

        # 触发告警检查
        await self._check_error_alert(error_record)

        # 对于严重错误，调用自定义 recovery 处理器（如果已注册）
        handler = self.error_handlers.get(type(Exception(error_record.error_message)))
        if handler:
            try:
                await handler(error_record)
            except Exception as exc:
                loguru_logger.error(f"Recovery handler failed: {exc}")

    async def _handle_network_exception(self, error_record: ErrorRecord):
        """处理网络异常"""
        loguru_logger.warning(f"Network error: {error_record.error_message}")

    async def _handle_database_exception(self, error_record: ErrorRecord):
        """处理数据库异常"""
        loguru_logger.error(f"Database error: {error_record.error_message}")

    async def _handle_authentication_exception(self, error_record: ErrorRecord):
        """处理认证异常"""
        loguru_logger.warning(f"Authentication error: {error_record.error_message}")

    async def _handle_validation_exception(self, error_record: ErrorRecord):
        """处理验证异常"""
        loguru_logger.info(f"Validation error: {error_record.error_message}")

    async def _check_error_alert(self, error_record: ErrorRecord):
        """检查是否需要告警"""
        threshold = self.alert_thresholds.get(error_record.severity, 0)

        if threshold > 0:
            # 检查最近错误数量
            recent_errors = [
                e
                for e in self.error_records
                if e.category == error_record.category
                and e.timestamp > datetime.now() - timedelta(minutes=5)
            ]

            if len(recent_errors) >= threshold:
                await self._send_error_alert(error_record, len(recent_errors))

    async def _send_error_alert(self, error_record: ErrorRecord, count: int):
        """发送错误告警"""
        loguru_logger.critical(f"Error alert triggered: {  # noqa: E501
                error_record.error_type} occurred {count} times in last 5 minutes")
        # 这里可以集成通知系统

    def register_error_handler(self, exception_type: Type[Exception], handler: Callable):
        """注册错误处理器"""
        self.error_handlers[exception_type] = handler
        loguru_logger.info(f"Registered error handler for {exception_type.__name__}")

    def register_retry_policy(self, name: str, policy: RetryPolicy):
        """注册重试策略"""
        self.retry_policies[name] = policy
        loguru_logger.info(f"Registered retry policy: {name}")

    def with_retry(self, policy_name: str = "default"):
        """重试装饰器"""

        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                policy = self.retry_policies.get(policy_name, self.retry_policies["default"])

                for attempt in range(policy.max_attempts):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        if attempt == policy.max_attempts - 1:
                            # 最后一次尝试失败，重新抛出异常
                            raise

                        # 检查是否应该重试
                        if policy.retry_on and not any(
                            isinstance(e, exc) for exc in policy.retry_on
                        ):
                            raise

                        # 计算延迟
                        delay = min(
                            policy.initial_delay * (policy.backoff_factor**attempt),
                            policy.max_delay,
                        )

                        loguru_logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}, "
                            f"retrying in {delay:.2f}s: {e}"
                        )

                        await asyncio.sleep(delay)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                policy = self.retry_policies.get(policy_name, self.retry_policies["default"])

                for attempt in range(policy.max_attempts):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == policy.max_attempts - 1:
                            raise

                        if policy.retry_on and not any(
                            isinstance(e, exc) for exc in policy.retry_on
                        ):
                            raise

                        delay = min(
                            policy.initial_delay * (policy.backoff_factor**attempt),
                            policy.max_delay,
                        )

                        loguru_logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}, "
                            f"retrying in {delay:.2f}s: {e}"
                        )

                        time.sleep(delay)

            # 根据函数类型返回适当的包装器
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    async def get_error_record(self, error_id: str) -> Optional[ErrorRecord]:
        """获取错误记录"""
        return self.error_index.get(error_id)

    async def get_error_statistics(self) -> Dict[str, Any]:
        """获取错误统计"""
        return {
            "total_errors": len(self.error_records),
            "by_category": {
                category.value: sum(1 for e in self.error_records if e.category == category)
                for category in ErrorCategory
            },
            "by_severity": {
                severity.value: sum(1 for e in self.error_records if e.severity == severity)
                for severity in ErrorSeverity
            },
            "error_statistics": dict(self.error_statistics),
            "recent_errors": len(
                [e for e in self.error_records if e.timestamp > datetime.now() - timedelta(hours=1)]
            ),
        }


class StructuredLogger:
    """结构化日志记录器"""

    def __init__(self):
        """初始化结构化日志记录器"""
        self.log_entries: deque = deque(maxlen=100000)
        self.log_format = LogFormat.STRUCTURED

        # 配置loguru
        self._configure_loguru()

    def _configure_loguru(self):
        """配置loguru"""
        # 移除默认处理器
        loguru_logger.remove()

        # 添加控制台处理器
        loguru_logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            level="INFO",
        )

        # 添加文件处理器
        loguru_logger.add(
            "logs/application_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            format=(  # noqa: E501
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
            ),
            level="DEBUG",
        )

        # 添加错误日志文件
        loguru_logger.add(
            "logs/error_{time:YYYY-MM-DD}.log",
            rotation="00:00",
            retention="30 days",
            format=(  # noqa: E501
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
            ),
            level="ERROR",
        )

    def log(self, level: str, message: str, **context):
        """记录日志"""
        # 记录到loguru
        loguru_logger.opt(depth=1).log(level, message, **context)

        # 记录到结构化日志
        import inspect

        frame = inspect.currentframe()

        # Get caller information safely
        caller_frame = frame.f_back if frame else None
        module = caller_frame.f_globals.get("__name__", "unknown") if caller_frame else "unknown"
        function = caller_frame.f_code.co_name if caller_frame else "unknown"
        line = caller_frame.f_lineno if caller_frame else 0

        log_entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            module=module,
            function=function,
            line=line,
            context=context,
        )

        self.log_entries.append(log_entry)

    def debug(self, message: str, **context):
        """记录DEBUG级别日志"""
        self.log("DEBUG", message, **context)

    def info(self, message: str, **context):
        """记录INFO级别日志"""
        self.log("INFO", message, **context)

    def warning(self, message: str, **context):
        """记录WARNING级别日志"""
        self.log("WARNING", message, **context)

    def error(self, message: str, **context):
        """记录ERROR级别日志"""
        self.log("ERROR", message, **context)

    def critical(self, message: str, **context):
        """记录CRITICAL级别日志"""
        self.log("CRITICAL", message, **context)

    async def get_log_entries(
        self,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """获取日志条目"""
        entries = []

        for entry in self.log_entries:
            # 应用过滤条件
            if level and entry.level != level:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            entries.append(entry)

            if len(entries) >= limit:
                break

        return entries

    async def get_log_statistics(self) -> Dict[str, Any]:
        """获取日志统计"""
        level_counts: Dict[str, int] = defaultdict(int)
        for entry in self.log_entries:
            level_counts[entry.level] += 1

        return {
            "total_entries": len(self.log_entries),
            "by_level": dict(level_counts),
            "log_format": self.log_format.value,
        }


class ErrorHandlingAndLogging:
    """错误处理和日志模块"""

    def __init__(self):
        """初始化错误处理和日志模块"""
        self.error_handler = ErrorHandler()
        self.structured_logger = StructuredLogger()

    async def initialize(self):
        """初始化"""
        await self.error_handler.initialize()
        loguru_logger.info("Error Handling and Logging module initialized")

    async def handle_exception(
        self, exception: Exception, context: Optional[Dict[str, Any]] = None
    ) -> ErrorRecord:
        """处理异常"""
        return await self.error_handler.handle_exception(exception, context)

    def log(self, level: str, message: str, **context):
        """记录日志"""
        self.structured_logger.log(level, message, **context)

    def debug(self, message: str, **context):
        """记录DEBUG日志"""
        self.structured_logger.debug(message, **context)

    def info(self, message: str, **context):
        """记录INFO日志"""
        self.structured_logger.info(message, **context)

    def warning(self, message: str, **context):
        """记录WARNING日志"""
        self.structured_logger.warning(message, **context)

    def error(self, message: str, **context):
        """记录ERROR日志"""
        self.structured_logger.error(message, **context)

    def critical(self, message: str, **context):
        """记录CRITICAL日志"""
        self.structured_logger.critical(message, **context)

    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "error_statistics": await self.error_handler.get_error_statistics(),
            "log_statistics": await self.structured_logger.get_log_statistics(),
        }


# 全局实例
error_handling_logging = ErrorHandlingAndLogging()
logger = error_handling_logging.structured_logger
