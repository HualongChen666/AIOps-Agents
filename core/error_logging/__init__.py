# -*- coding: utf-8 -*-
"""
错误日志模块

导出错误日志记录器、处理器、告警功能和FastAPI处理器。
"""

from .alerting import check_error_alerts, get_error_alert_manager
from .fastapi_handlers import setup_exception_handlers
from .handler import get_error_count, get_error_log_handler, get_error_stats, record_error
from .logger import get_structured_error_logger, log_error, log_exception

__all__ = [
    "log_error",
    "log_exception",
    "get_structured_error_logger",
    "record_error",
    "get_error_stats",
    "get_error_count",
    "get_error_log_handler",
    "get_error_alert_manager",
    "check_error_alerts",
    "setup_exception_handlers",
]
