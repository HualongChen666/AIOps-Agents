# -*- coding: utf-8 -*-
"""
外部API审计中间件
External API Audit Middleware

为所有外部API调用提供统一的审计日志和安全监控
"""

import json
import os
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, List, Optional

from loguru import logger


class ExternalAPIAuditLogger:
    """
    外部API审计日志记录器

    记录所有外部API调用的详细信息，包括：
    - 请求URL、方法、头部、主体
    - 响应状态、耗时、错误信息
    - 调用者信息、时间戳
    """

    def __init__(self, max_log_entries: int = 10000):
        self._audit_enabled = True
        self._sensitive_headers = {"authorization", "x-api-key", "cookie", "set-cookie"}
        self._audit_logs: deque[Dict[str, Any]] = deque(
            maxlen=max_log_entries
        )  # In-memory log storage
        self._max_log_entries = max_log_entries

    def log_api_call(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        response_status: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        error: Optional[str] = None,
        caller: Optional[str] = None,
    ):
        """
        记录API调用审计日志

        Args:
            method: HTTP方法
            url: 请求URL
            headers: 请求头部（敏感信息会被过滤）
            body: 请求主体
            response_status: 响应状态码
            response_time_ms: 响应时间（毫秒）
            error: 错误信息
            caller: 调用者信息
        """
        if not self._audit_enabled:
            return

        # 过滤敏感头部信息
        safe_headers = {}
        if headers:
            for key, value in headers.items():
                if key.lower() in self._sensitive_headers:
                    safe_headers[key] = "***REDACTED***"
                else:
                    safe_headers[key] = value

        # 构建审计记录
        audit_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": "external_api_call",
            "method": method,
            "url": self._sanitize_url(url),
            "headers": safe_headers,
            "body_size": len(str(body)) if body else 0,
            "response_status": response_status,
            "response_time_ms": response_time_ms,
            "error": error,
            "caller": caller or "unknown",
        }

        # 根据结果选择日志级别
        if error:
            logger.error(f"External API call failed: {json.dumps(audit_record, default=str)}")
        elif response_status and response_status >= 400:
            logger.warning(
                f"External API call returned error status: {json.dumps(audit_record, default=str)}"
            )
        else:
            logger.info(f"External API call: {json.dumps(audit_record, default=str)}")

        # 存储到内存审计日志
        self._audit_logs.append(audit_record)

    def _sanitize_url(self, url: str) -> str:
        """
        清理URL中的敏感信息

        Args:
            url: 原始URL

        Returns:
            清理后的URL
        """
        # 移除URL中的查询参数中的敏感信息
        if "?" in url:
            base, query = url.split("?", 1)
            # 简单的查询参数清理（可以根据需要扩展）
            return base + "?***"
        return url

    def enable_audit(self):
        """启用审计日志"""
        self._audit_enabled = True
        logger.info("External API audit logging enabled")

    def disable_audit(self):
        """禁用审计日志"""
        self._audit_enabled = False
        logger.warning("External API audit logging disabled")

    def query_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        method: Optional[str] = None,
        url_pattern: Optional[str] = None,
        min_status: Optional[int] = None,
        max_status: Optional[int] = None,
        caller: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        查询审计日志

        Args:
            start_time: 开始时间
            end_time: 结束时间
            method: HTTP方法过滤
            url_pattern: URL模式匹配
            min_status: 最小状态码
            max_status: 最大状态码
            caller: 调用者过滤
            limit: 返回结果数量限制

        Returns:
            审计日志列表
        """
        results = []

        for log_entry in self._audit_logs:
            # 时间过滤
            if start_time:
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                if log_time < start_time:
                    continue

            if end_time:
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                if log_time > end_time:
                    continue

            # 方法过滤
            if method and log_entry.get("method") != method.upper():
                continue

            # URL模式过滤
            if url_pattern and url_pattern.lower() not in log_entry.get("url", "").lower():
                continue

            # 状态码过滤
            status = log_entry.get("response_status")
            if min_status and status and status < min_status:
                continue
            if max_status and status and status > max_status:
                continue

            # 调用者过滤
            if caller and caller != log_entry.get("caller"):
                continue

            results.append(log_entry)

            if len(results) >= limit:
                break

        return results

    def get_audit_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取审计日志摘要统计

        Args:
            hours: 统计最近多少小时的日志

        Returns:
            审计摘要信息
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        total_calls = 0
        failed_calls = 0
        slow_calls = 0
        method_counts: Dict[str, int] = {}
        caller_counts: Dict[str, int] = {}

        for log_entry in self._audit_logs:
            log_time = datetime.fromisoformat(log_entry["timestamp"])

            if log_time < cutoff_time:
                continue

            total_calls += 1

            # 统计失败调用
            if log_entry.get("error") or (log_entry.get("response_status", 0) >= 400):
                failed_calls += 1

            # 统计慢调用（超过1秒）
            response_time_ms = log_entry.get("response_time_ms") or 0
            if response_time_ms > 1000:
                slow_calls += 1

            # 统计方法分布
            method = log_entry.get("method", "UNKNOWN")
            method_counts[method] = method_counts.get(method, 0) + 1

            # 统计调用者分布
            caller = log_entry.get("caller", "unknown")
            caller_counts[caller] = caller_counts.get(caller, 0) + 1

        return {
            "time_range_hours": hours,
            "total_calls": total_calls,
            "failed_calls": failed_calls,
            "success_rate": (total_calls - failed_calls) / total_calls if total_calls > 0 else 0,
            "slow_calls": slow_calls,
            "method_distribution": method_counts,
            "caller_distribution": caller_counts,
            "current_log_size": len(self._audit_logs),
            "max_log_entries": self._max_log_entries,
        }

    def clear_audit_logs(self, older_than_hours: Optional[int] = None):
        """
        清理审计日志

        Args:
            older_than_hours: 清理多少小时之前的日志，None表示清理全部
        """
        if older_than_hours is None:
            self._audit_logs.clear()
            logger.info("All audit logs cleared")
        else:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=older_than_hours)
            original_size = len(self._audit_logs)

            # 保留最近的日志
            filtered_logs: deque[Dict[str, Any]] = deque(maxlen=self._max_log_entries)
            for log_entry in self._audit_logs:
                log_time = datetime.fromisoformat(log_entry["timestamp"])
                if log_time >= cutoff_time:
                    filtered_logs.append(log_entry)

            self._audit_logs = filtered_logs
            logger.info(
                f"Cleared {original_size - len(self._audit_logs)} audit logs older than "
                f"{older_than_hours} hours"
            )

    def export_audit_logs(self, format: str = "json") -> str:
        """
        导出审计日志

        Args:
            format: 导出格式（json或csv）

        Returns:
            导出的日志字符串
        """
        if format == "json":
            return json.dumps(list(self._audit_logs), indent=2, default=str)
        elif format == "csv":
            import csv
            import io

            if not self._audit_logs:
                return ""

            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=self._audit_logs[0].keys())
            writer.writeheader()
            writer.writerows(self._audit_logs)

            return output.getvalue()
        else:
            raise ValueError(f"Unsupported export format: {format}")


# 全局审计日志记录器实例
_global_audit_logger: Optional[ExternalAPIAuditLogger] = None


def get_audit_logger() -> ExternalAPIAuditLogger:
    """获取全局审计日志记录器"""
    global _global_audit_logger
    if _global_audit_logger is None:
        _global_audit_logger = ExternalAPIAuditLogger()
    return _global_audit_logger


def audit_httpx_call(func):
    """
    httpx调用审计装饰器

    用于装饰httpx客户端的方法，自动记录审计日志
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        audit_logger = get_audit_logger()
        start_time = time.time()

        # 提取请求信息
        method = kwargs.get("method", "GET")
        url = kwargs.get("url", "")
        headers = kwargs.get("headers", {})
        content = kwargs.get("content", None)

        try:
            result = await func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # 记录成功调用
            audit_logger.log_api_call(
                method=method,
                url=str(url),
                headers=dict(headers) if headers else None,
                body=content,
                response_status=result.status_code if hasattr(result, "status_code") else None,
                response_time_ms=response_time,
                caller=func.__name__,
            )

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            # 记录失败调用
            audit_logger.log_api_call(
                method=method,
                url=str(url),
                headers=dict(headers) if headers else None,
                body=content,
                response_time_ms=response_time,
                error=str(e),
                caller=func.__name__,
            )

            raise

    return wrapper


def audit_aiohttp_call(func):
    """
    aiohttp调用审计装饰器

    用于装饰aiohttp客户端的方法，自动记录审计日志
    """

    @wraps(func)
    async def wrapper(*args, **kwargs):
        audit_logger = get_audit_logger()
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            response_time = (time.time() - start_time) * 1000

            # 对于aiohttp，我们需要从上下文中提取更多信息
            # 这里简化处理，可以根据需要扩展
            audit_logger.log_api_call(
                method="UNKNOWN",
                url="aiohttp_call",
                response_time_ms=response_time,
                caller=func.__name__,
            )

            return result

        except Exception as e:
            response_time = (time.time() - start_time) * 1000

            audit_logger.log_api_call(
                method="UNKNOWN",
                url="aiohttp_call",
                response_time_ms=response_time,
                error=str(e),
                caller=func.__name__,
            )

            raise

    return wrapper


def initialize_external_api_audit():
    """
    初始化外部API审计

    在应用启动时调用，设置审计配置
    """
    audit_logger = get_audit_logger()

    # 根据环境变量决定是否启用审计
    audit_enabled = os.getenv("EXTERNAL_API_AUDIT_ENABLED", "true").lower() == "true"

    if audit_enabled:
        audit_logger.enable_audit()
    else:
        audit_logger.disable_audit()

    logger.info(f"External API audit initialized (enabled={audit_enabled})")


# 导出便捷函数和装饰器
__all__ = [
    "ExternalAPIAuditLogger",
    "get_audit_logger",
    "audit_httpx_call",
    "audit_aiohttp_call",
    "initialize_external_api_audit",
]
