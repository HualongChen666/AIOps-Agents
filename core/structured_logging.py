# -*- coding: utf-8 -*-
"""
Structured Logging Module
结构化日志模块

Provides structured logging capabilities for the AIOps Agent system.
Includes log formatting, context management, and log level configuration.
"""

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, cast

from loguru import logger as loguru_logger

# Import logging context manager
try:
    from core.logging.context import get_logging_context

    CONTEXT_AVAILABLE = True
except ImportError:
    CONTEXT_AVAILABLE = False
    get_logging_context = None  # type: ignore[assignment]


class StructuredLogger:
    """Structured logger with JSON formatting and context management"""

    def __init__(self, name: str, log_dir: str = "logs"):
        """
        Initialize structured logger

        Args:
            name: Logger name
            log_dir: Directory for log files
        """
        self.name = name
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create standard Python logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)

        # Remove existing handlers
        self.logger.handlers.clear()

        # Setup file handler with JSON formatting
        self._setup_file_handler()

        # Setup console handler
        self._setup_console_handler()

    def _setup_file_handler(self):
        """Setup file handler with JSON formatting"""
        log_file = self.log_dir / f"{self.name}.jsonl"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JsonFormatter())
        self.logger.addHandler(file_handler)

    def _setup_console_handler(self):
        """Setup console handler with readable formatting"""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        self.logger.addHandler(console_handler)

    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False,
    ):
        """
        Log a message with structured context

        Args:
            level: Log level (logging.INFO, logging.ERROR, etc.)
            message: Log message
            extra: Additional context data
            exc_info: Include exception information
        """
        # Create structured log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": logging.getLevelName(level),
            "logger": self.name,
            "message": message,
            "context": extra or {},
        }

        # Automatically inject context from context manager
        if CONTEXT_AVAILABLE and get_logging_context:  # type: ignore[truthy-function]
            try:
                context_data = get_logging_context().to_dict()
                context_dict = cast(Dict[str, Any], log_entry["context"])
                context_dict.update(context_data)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                loguru_logger.debug("Context injection failed, continuing", exc_info=True)

        # Add request ID if available (legacy support)
        if hasattr(self, "_request_id"):
            context_dict = cast(Dict[str, Any], log_entry["context"])
            context_dict["request_id"] = self._request_id

        # Add exception info if available
        if exc_info:
            context_dict = cast(Dict[str, Any], log_entry["context"])
            context_dict["exception"] = True

        # Log with standard Python logger
        self.logger.log(level, message, extra={"structured_log": log_entry}, exc_info=exc_info)

    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log(logging.DEBUG, message, kwargs)

    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log(logging.INFO, message, kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log(logging.WARNING, message, kwargs)

    def error(self, message: str, **kwargs):
        """Log error message"""
        self._log(logging.ERROR, message, kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self._log(logging.CRITICAL, message, kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self._log(logging.ERROR, message, kwargs, exc_info=True)

    def set_request_id(self, request_id: str):
        """Set request ID context"""
        self._request_id = request_id

    def clear_request_id(self):
        """Clear request ID context"""
        if hasattr(self, "_request_id"):
            delattr(self, "_request_id")


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add structured log if available
        if hasattr(record, "structured_log"):
            log_entry.update(record.structured_log)

        # Add exception info if available
        if record.exc_info:
            exc_type = record.exc_info[0]
            exc_value = record.exc_info[1]
            log_entry["exception"] = {
                "type": exc_type.__name__ if exc_type else "Unknown",
                "message": str(exc_value) if exc_value else "Unknown",
                "traceback": self.formatException(record.exc_info),
            }

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Console formatter for human-readable output"""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record for console"""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        level = record.levelname.ljust(8)
        message = record.getMessage()

        return f"{timestamp} [{level}] {record.name}: {message}"


class RequestContext:
    """Request context for tracking request-specific information"""

    def __init__(self):
        """Initialize request context"""
        self.request_id = str(uuid.uuid4())
        self.start_time = time.time()
        self.user_id: Optional[str] = None
        self.client_ip: Optional[str] = None
        self.metadata: Dict[str, Any] = {}

    def set_user(self, user_id: str):
        """Set user ID"""
        self.user_id = user_id

    def set_client_ip(self, client_ip: str):
        """Set client IP"""
        self.client_ip = client_ip

    def add_metadata(self, key: str, value: Any):
        """Add metadata"""
        self.metadata[key] = value

    def get_duration(self) -> float:
        """Get request duration"""
        return time.time() - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "request_id": self.request_id,
            "user_id": self.user_id,
            "client_ip": self.client_ip,
            "duration": self.get_duration(),
            "metadata": self.metadata,
        }


# Global logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """
    Get or create a structured logger

    Args:
        name: Logger name

    Returns:
        StructuredLogger instance
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


def setup_logging(log_dir: str = "logs", log_level: str = "INFO"):
    """
    Setup global logging configuration

    Args:
        log_dir: Directory for log files
        log_level: Global log level
    """
    # Create log directory
    Path(log_dir).mkdir(exist_ok=True)

    # Configure loguru
    loguru_logger.remove()  # Remove default handler

    # Add file handler
    loguru_logger.add(
        f"{log_dir}/aiops_{{time:YYYY-MM-DD}}.log",
        rotation="00:00",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )

    # Add console handler
    loguru_logger.add(
        lambda msg: print(msg, end=""),
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
    )

    loguru_logger.info("Structured logging initialized")


def setup_loki_logging(loki_url: str, service_name: str = "aiops-agent") -> bool:
    """
    Ship structured logs to a Grafana Loki instance.

    Adds a Loguru sink that batches log records and pushes them to Loki's
    /loki/api/v1/push endpoint. If the push fails, the error is silently ignored
    so that application logging is never blocked by network issues.

    Args:
        loki_url: Base URL of the Loki instance (e.g. http://localhost:3100).
        service_name: Service label attached to every log stream.

    Returns:
        True if the sink was registered, False otherwise.
    """
    try:
        import urllib.request
        from urllib.error import URLError

        endpoint = f"{loki_url.rstrip('/')}/loki/api/v1/push"

        def loki_sink(message: str) -> None:
            """Best-effort Loki log shipper."""
            try:
                record = (
                    message.record if hasattr(message, "record") else None
                )  # type: ignore[union-attr]
                ts_ns = str(int(time.time() * 1_000_000_000))
                labels = {"service_name": service_name, "level": "INFO"}
                if record and hasattr(record, "level"):
                    labels["level"] = record.level.name  # type: ignore[union-attr]
                payload = {
                    "streams": [
                        {
                            "stream": labels,
                            "values": [[ts_ns, message.strip()]],
                        }
                    ]
                }
                data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    endpoint,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=2) as resp:  # nosec B310
                    resp.read()
            except URLError:
                logging.warning("Suppressed exception", exc_info=True)
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)

        loguru_logger.add(loki_sink, level="INFO", format="{message}")
        return True
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        return False