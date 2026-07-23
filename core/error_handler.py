# -*- coding: utf-8 -*-
"""
Enhanced Error Handling and Logging Module
==========================================

Comprehensive error handling and logging system including:
- Unified exception handling mechanism
- Detailed error context information
- Error classification and severity levels
- Error retry and recovery strategies
- Structured logging with multiple outputs
- Error alerting and notification
"""

import asyncio
import functools
import json
import sys
import threading
import time
import traceback
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


class ErrorSeverity(Enum):
    """Error severity levels"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    FATAL = "fatal"


class ErrorCategory(Enum):
    """Error categories"""

    VALIDATION = "validation"
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_SERVICE = "external_service"
    SYSTEM = "system"
    UNKNOWN = "unknown"


@dataclass
class ErrorContext:
    """Error context information"""

    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    component: Optional[str] = None
    function_name: Optional[str] = None
    additional_context: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    resolved: bool = False


class AIOpsException(Exception):
    """Base exception for AIOps Agent"""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.severity = severity
        self.category = category
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary"""
        return {
            "message": self.message,
            "severity": self.severity.value,
            "category": self.category.value,
            "context": self.context,
            "type": self.__class__.__name__,
        }


class ValidationError(AIOpsException):
    """Validation error"""

    def __init__(self, message: str, field: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.VALIDATION,
            context={"field": field, **context},
        )


class NetworkError(AIOpsException):
    """Network error"""

    def __init__(self, message: str, url: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.NETWORK,
            context={"url": url, **context},
        )


class DatabaseError(AIOpsException):
    """Database error"""

    def __init__(self, message: str, query: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.DATABASE,
            context={"query": query, **context},
        )


class AuthenticationError(AIOpsException):
    """Authentication error"""

    def __init__(self, message: str, user_id: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.AUTHENTICATION,
            context={"user_id": user_id, **context},
        )


class AuthorizationError(AIOpsException):
    """Authorization error"""

    def __init__(self, message: str, resource: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.AUTHORIZATION,
            context={"resource": resource, **context},
        )


class ExternalServiceError(AIOpsException):
    """External service error"""

    def __init__(self, message: str, service: Optional[str] = None, **context):
        super().__init__(
            message,
            severity=ErrorSeverity.ERROR,
            category=ErrorCategory.EXTERNAL_SERVICE,
            context={"service": service, **context},
        )


class ErrorHandler:
    """
    Comprehensive error handler
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize error handler

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Error storage
        self.error_history: List[ErrorContext] = []
        self.error_stats: Dict[str, int] = defaultdict(int)
        self.error_patterns: Dict[str, List[ErrorContext]] = defaultdict(list)

        # Retry configuration
        self.retry_config = self._initialize_retry_config()

        # Alert configuration
        self.alert_config = self._initialize_alert_config()
        self.alert_queue: List[ErrorContext] = []

        # Logging configuration
        self._configure_logging()

        # Background alert processing
        self._start_alert_processor()

        logger.info("Error Handler initialized")

    def _initialize_retry_config(self) -> Dict[str, Any]:
        """Initialize retry configuration"""
        return {
            "max_retries": 3,
            "base_delay": 1.0,  # seconds
            "max_delay": 60.0,
            "exponential_backoff": True,
            "retryable_errors": ["NetworkError", "ExternalServiceError", "TimeoutError"],
        }

    def _initialize_alert_config(self) -> Dict[str, Any]:
        """Initialize alert configuration"""
        return {
            "alert_on_critical": True,
            "alert_on_fatal": True,
            "alert_threshold": 5,  # Alert after N errors of same type
            "alert_window": 300,  # seconds
            "notification_channels": ["log"],
        }

    def _configure_logging(self):
        """Configure structured logging"""
        # Remove default handler
        logger.remove()

        # Add console handler with structured output
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            level="INFO",
            enqueue=True,
        )

        # Add file handler for errors
        logger.add(
            "logs/errors.log",
            format=(  # noqa: E501
                "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
            ),
            level="ERROR",
            rotation="500 MB",
            retention="30 days",
        )

        # Add structured JSON file handler
        logger.add(
            "logs/structured.json",
            format="{message}",
            level="DEBUG",
            serialize=True,
            rotation="500 MB",
            retention="30 days",
        )

    def _start_alert_processor(self):
        """Start background alert processor"""
        alert_thread = threading.Thread(target=self._alert_processing_loop, daemon=True)
        alert_thread.start()
        logger.info("Alert processor started")

    def _alert_processing_loop(self):
        """Background alert processing loop"""
        while True:
            try:
                self._process_alerts()
                time.sleep(10)  # Process alerts every 10 seconds
            except Exception as e:
                logger.error(f"Alert processing error: {e}")
                time.sleep(10)

    def _process_alerts(self):
        """Process queued alerts"""
        while self.alert_queue:
            error_context = self.alert_queue.pop(0)
            self._send_alert(error_context)

    def _send_alert(self, error_context: ErrorContext):
        """Send error alert"""
        alert_data = {
            "error_id": error_context.error_id,
            "severity": error_context.severity.value,
            "category": error_context.category.value,
            "message": error_context.error_message,
            "component": error_context.component,
            "timestamp": error_context.timestamp.isoformat(),
        }

        logger.critical("ERROR ALERT: {alert}", alert=json.dumps(alert_data))

        # Here you could add integration with notification systems
        # e.g., Slack, email, PagerDuty, etc.

    def handle_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        request_id: Optional[str] = None,
    ) -> ErrorContext:
        """
        Handle an exception with full context

        Args:
            exception: Exception to handle
            context: Additional context
            user_id: User identifier
            request_id: Request identifier

        Returns:
            ErrorContext
        """
        error_id = f"error_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

        # Determine severity and category
        severity = ErrorSeverity.ERROR
        category = ErrorCategory.UNKNOWN

        if isinstance(exception, AIOpsException):
            severity = exception.severity
            category = exception.category
        elif isinstance(exception, (ValueError, TypeError)):
            severity = ErrorSeverity.WARNING
            category = ErrorCategory.VALIDATION
        elif isinstance(exception, (ConnectionError, TimeoutError)):
            severity = ErrorSeverity.ERROR
            category = ErrorCategory.NETWORK

        # Get stack trace
        stack_trace = "".join(
            traceback.format_exception(type(exception), exception, exception.__traceback__)
        )

        # Get function name from stack trace
        function_name = None
        if exception.__traceback__:
            frame = exception.__traceback__.tb_frame
            function_name = frame.f_code.co_name
            component = frame.f_globals.get("__name__")
        else:
            component = context.get("component") if context else None

        # Create error context
        error_context = ErrorContext(
            error_id=error_id,
            error_type=exception.__class__.__name__,
            error_message=str(exception),
            severity=severity,
            category=category,
            stack_trace=stack_trace,
            user_id=user_id,
            request_id=request_id,
            component=component,
            function_name=function_name,
            additional_context=context or {},
        )

        # Store error
        self.error_history.append(error_context)
        self.error_stats[f"{category.value}:{exception.__class__.__name__}"] += 1
        self.error_patterns[exception.__class__.__name__].append(error_context)

        # Log error
        self._log_error(error_context)

        # Queue alert if needed
        if severity in [ErrorSeverity.CRITICAL, ErrorSeverity.FATAL]:
            self.alert_queue.append(error_context)

        return error_context

    def _log_error(self, error_context: ErrorContext):
        """Log error with appropriate level"""
        log_data = {
            "error_id": error_context.error_id,
            "error_type": error_context.error_type,
            "severity": error_context.severity.value,
            "category": error_context.category.value,
            "component": error_context.component,
            "function": error_context.function_name,
            "user_id": error_context.user_id,
            "request_id": error_context.request_id,
            "context": error_context.additional_context,
        }

        if error_context.severity == ErrorSeverity.DEBUG:
            logger.debug("{message}", message=json.dumps(log_data), extra={"structured": log_data})
        elif error_context.severity == ErrorSeverity.INFO:
            logger.info("{message}", message=json.dumps(log_data), extra={"structured": log_data})
        elif error_context.severity == ErrorSeverity.WARNING:
            logger.warning(
                "{message}", message=json.dumps(log_data), extra={"structured": log_data}
            )
        elif error_context.severity == ErrorSeverity.ERROR:
            logger.error("{message}", message=json.dumps(log_data), extra={"structured": log_data})
        elif error_context.severity == ErrorSeverity.CRITICAL:
            logger.critical(
                "{message}", message=json.dumps(log_data), extra={"structured": log_data}
            )
        elif error_context.severity == ErrorSeverity.FATAL:
            logger.critical(
                "{message}", message=json.dumps(log_data), extra={"structured": log_data}
            )
            # Log stack trace for fatal errors
            if error_context.stack_trace:
                logger.critical(f"Stack trace:\n{error_context.stack_trace}")

    def retry(
        self,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        exponential_backoff: Optional[bool] = None,
    ):
        """
        Decorator for retrying functions on failure

        Args:
            max_retries: Maximum number of retries
            base_delay: Base delay between retries
            exponential_backoff: Whether to use exponential backoff
        """

        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                nonlocal max_retries, base_delay, exponential_backoff

                max_retries = max_retries or self.retry_config["max_retries"]
                base_delay = base_delay or self.retry_config["base_delay"]
                exponential_backoff = (
                    exponential_backoff
                    if exponential_backoff is not None
                    else self.retry_config["exponential_backoff"]
                )

                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e

                        # Check if error is retryable
                        error_type = e.__class__.__name__
                        if error_type not in self.retry_config["retryable_errors"]:
                            self.handle_exception(
                                e, context={"retry_attempt": attempt, "non_retryable": True}
                            )
                            raise

                        # Log retry attempt
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )

                        # Calculate delay
                        if exponential_backoff:
                            delay = min(base_delay * (2**attempt), self.retry_config["max_delay"])
                        else:
                            delay = base_delay

                        # Wait before retry
                        await asyncio.sleep(delay)

                # All retries exhausted
                if last_exception is not None:
                    self.handle_exception(
                        last_exception,
                        context={"retry_exhausted": True, "max_retries": max_retries},
                    )
                    raise last_exception
                else:
                    # This should never happen, but handle it for type safety
                    raise RuntimeError("All retries exhausted but no exception was captured")

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                nonlocal max_retries, base_delay, exponential_backoff

                max_retries = max_retries or self.retry_config["max_retries"]
                base_delay = base_delay or self.retry_config["base_delay"]
                exponential_backoff = (
                    exponential_backoff
                    if exponential_backoff is not None
                    else self.retry_config["exponential_backoff"]
                )

                last_exception = None

                for attempt in range(max_retries + 1):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        last_exception = e

                        # Check if error is retryable
                        error_type = e.__class__.__name__
                        if error_type not in self.retry_config["retryable_errors"]:
                            self.handle_exception(
                                e, context={"retry_attempt": attempt, "non_retryable": True}
                            )
                            raise

                        # Log retry attempt
                        logger.warning(
                            f"Retry attempt {attempt + 1}/{max_retries} for {func.__name__}: {e}"
                        )

                        # Calculate delay
                        if exponential_backoff:
                            delay = min(base_delay * (2**attempt), self.retry_config["max_delay"])
                        else:
                            delay = base_delay

                        # Wait before retry
                        time.sleep(delay)

                # All retries exhausted
                if last_exception is not None:
                    self.handle_exception(
                        last_exception,
                        context={"retry_exhausted": True, "max_retries": max_retries},
                    )
                    raise last_exception
                else:
                    # This should never happen, but handle it for type safety
                    raise RuntimeError("All retries exhausted but no exception was captured")

            # Return appropriate wrapper based on function type
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        return {
            "total_errors": len(self.error_history),
            "errors_by_type": dict(self.error_stats),
            "errors_by_severity": self._count_by_severity(),
            "errors_by_category": self._count_by_category(),
            "recent_errors": [
                {
                    "error_id": e.error_id,
                    "error_type": e.error_type,
                    "severity": e.severity.value,
                    "category": e.category.value,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.error_history[-20:]
            ],
        }

    def _count_by_severity(self) -> Dict[str, int]:
        """Count errors by severity"""
        counts: Dict[str, int] = defaultdict(int)
        for error in self.error_history:
            counts[error.severity.value] += 1
        return dict(counts)

    def _count_by_category(self) -> Dict[str, int]:
        """Count errors by category"""
        counts: Dict[str, int] = defaultdict(int)
        for error in self.error_history:
            counts[error.category.value] += 1
        return dict(counts)

    def get_error_report(self, hours: int = 24) -> Dict[str, Any]:
        """
        Generate error report for specified time period

        Args:
            hours: Number of hours to report on

        Returns:
            Error report
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff_time]

        return {
            "period_hours": hours,
            "total_errors": len(recent_errors),
            "errors_by_type": self._count_errors_by_type(recent_errors),
            "errors_by_severity": self._count_errors_by_severity(recent_errors),
            "errors_by_category": self._count_errors_by_category(recent_errors),
            "top_errors": self._get_top_errors(recent_errors, limit=10),
            "error_trends": self._calculate_error_trends(recent_errors),
        }

    def _count_errors_by_type(self, errors: List[ErrorContext]) -> Dict[str, int]:
        """Count errors by type"""
        counts: Dict[str, int] = defaultdict(int)
        for error in errors:
            counts[error.error_type] += 1
        return dict(counts)

    def _count_errors_by_severity(self, errors: List[ErrorContext]) -> Dict[str, int]:
        """Count errors by severity"""
        counts: Dict[str, int] = defaultdict(int)
        for error in errors:
            counts[error.severity.value] += 1
        return dict(counts)

    def _count_errors_by_category(self, errors: List[ErrorContext]) -> Dict[str, int]:
        """Count errors by category"""
        counts: Dict[str, int] = defaultdict(int)
        for error in errors:
            counts[error.category.value] += 1
        return dict(counts)

    def _get_top_errors(self, errors: List[ErrorContext], limit: int = 10) -> List[Dict[str, Any]]:
        """Get most frequent errors"""
        error_counts: Dict[str, int] = defaultdict(int)
        for error in errors:
            error_counts[error.error_type] += 1

        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)

        return [
            {
                "error_type": error_type,
                "count": count,
                "percentage": (count / len(errors)) * 100 if errors else 0,
            }
            for error_type, count in sorted_errors[:limit]
        ]

    def _calculate_error_trends(self, errors: List[ErrorContext]) -> Dict[str, Any]:
        """Calculate error trends"""
        # Group errors by hour
        hourly_counts: Dict[str, int] = defaultdict(int)
        for error in errors:
            hour_key = error.timestamp.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] += 1

        # Calculate trend
        hourly_values = list(hourly_counts.values())
        if len(hourly_values) >= 2:
            trend = (
                (hourly_values[-1] - hourly_values[-2]) / hourly_values[-2]
                if hourly_values[-2] > 0
                else 0
            )
        else:
            trend = 0

        return {
            "hourly_distribution": dict(hourly_counts),
            "trend_percentage": trend * 100,
            "trend_direction": (
                "increasing" if trend > 0 else "decreasing" if trend < 0 else "stable"
            ),
        }


# Global instance
error_handler = ErrorHandler()
