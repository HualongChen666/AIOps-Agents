# -*- coding: utf-8 -*-
"""
Unified API Response Module
统一API响应模块

提供标准化的API响应格式和错误处理。
"""

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from fastapi import HTTPException

T = TypeVar("T")


class ErrorCode(str, Enum):
    """标准错误码"""

    # 通用错误 (1xxx)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_ERROR = "AUTHENTICATION_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    BAD_REQUEST = "BAD_REQUEST"
    METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"

    # 告警相关错误 (2xxx)
    ALERT_NOT_FOUND = "ALERT_NOT_FOUND"
    ALERT_PROCESSING_FAILED = "ALERT_PROCESSING_FAILED"
    ALERT_INTELLIGENCE_UNAVAILABLE = "ALERT_INTELLIGENCE_UNAVAILABLE"
    ALERT_ROUTING_FAILED = "ALERT_ROUTING_FAILED"
    ALERT_SUPPRESSION_FAILED = "ALERT_SUPPRESSION_FAILED"

    # AI相关错误 (3xxx)
    AI_ANALYSIS_FAILED = "AI_ANALYSIS_FAILED"
    AI_ENGINE_UNAVAILABLE = "AI_ENGINE_UNAVAILABLE"
    AI_MODEL_LOAD_FAILED = "AI_MODEL_LOAD_FAILED"
    AI_PREDICTION_FAILED = "AI_PREDICTION_FAILED"
    AI_LEARNING_FAILED = "AI_LEARNING_FAILED"

    # 数据库错误 (4xxx)
    DATABASE_ERROR = "DATABASE_ERROR"
    DATABASE_CONNECTION_FAILED = "DATABASE_CONNECTION_FAILED"
    DATABASE_QUERY_FAILED = "DATABASE_QUERY_FAILED"
    DATABASE_TRANSACTION_FAILED = "DATABASE_TRANSACTION_FAILED"

    # 缓存错误 (5xxx)
    CACHE_ERROR = "CACHE_ERROR"
    CACHE_CONNECTION_FAILED = "CACHE_CONNECTION_FAILED"
    CACHE_MISS = "CACHE_MISS"

    # 权限错误 (6xxx)
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INSUFFICIENT_PRIVILEGES = "INSUFFICIENT_PRIVILEGES"
    TOKEN_EXPIRED = "TOKEN_" + "EXPIRED"
    TOKEN_INVALID = "TOKEN_" + "INVALID"

    # 混沌工程错误 (7xxx)
    CHAOS_STATUS_ERROR = "CHAOS_STATUS_ERROR"
    CHAOS_ENABLE_ERROR = "CHAOS_ENABLE_ERROR"
    CHAOS_DISABLE_ERROR = "CHAOS_DISABLE_ERROR"
    INVALID_EXPERIMENT = "INVALID_EXPERIMENT"
    EXPERIMENT_ERROR = "EXPERIMENT_ERROR"
    EXPERIMENT_HISTORY_ERROR = "EXPERIMENT_HISTORY_ERROR"

    # 云平台错误 (8xxx)
    CLOUD_PROVIDER_ERROR = "CLOUD_PROVIDER_ERROR"
    CLOUD_RESOURCE_NOT_FOUND = "CLOUD_RESOURCE_NOT_FOUND"
    CLOUD_QUOTA_EXCEEDED = "CLOUD_QUOTA_EXCEEDED"

    # Kubernetes错误 (9xxx)
    K8S_CLUSTER_ERROR = "K8S_CLUSTER_ERROR"
    K8S_POD_ERROR = "K8S_POD_ERROR"
    K8S_SERVICE_ERROR = "K8S_SERVICE_ERROR"
    K8S_DEPLOYMENT_ERROR = "K8S_DEPLOYMENT_ERROR"

    # 插件系统错误 (10xxx)
    PLUGIN_NOT_FOUND = "PLUGIN_NOT_FOUND"
    PLUGIN_LOAD_FAILED = "PLUGIN_LOAD_FAILED"
    PLUGIN_EXECUTE_FAILED = "PLUGIN_EXECUTE_FAILED"
    PLUGIN_VERSION_MISMATCH = "PLUGIN_VERSION_MISMATCH"

    # 工作流错误 (11xxx)
    WORKFLOW_NOT_FOUND = "WORKFLOW_NOT_FOUND"
    WORKFLOW_EXECUTION_FAILED = "WORKFLOW_EXECUTION_FAILED"
    WORKFLOW_VALIDATION_FAILED = "WORKFLOW_VALIDATION_FAILED"

    # 监控错误 (12xxx)
    METRIC_COLLECTION_FAILED = "METRIC_COLLECTION_FAILED"
    MONITORING_DATA_INVALID = "MONITORING_DATA_INVALID"
    ALERT_RULE_INVALID = "ALERT_RULE_INVALID"

    # 日志错误 (13xxx)
    LOG_COLLECTION_FAILED = "LOG_COLLECTION_FAILED"
    LOG_QUERY_FAILED = "LOG_QUERY_FAILED"
    LOG_STORAGE_ERROR = "LOG_STORAGE_ERROR"

    # 备份恢复错误 (14xxx)
    BACKUP_FAILED = "BACKUP_FAILED"
    RESTORE_FAILED = "RESTORE_FAILED"
    BACKUP_NOT_FOUND = "BACKUP_NOT_FOUND"

    # 修复系统错误 (15xxx)
    REPAIR_SCRIPT_NOT_FOUND = "REPAIR_SCRIPT_NOT_FOUND"
    REPAIR_EXECUTION_FAILED = "REPAIR_EXECUTION_FAILED"
    REPAIR_HISTORY_ERROR = "REPAIR_HISTORY_ERROR"

    # 集成错误 (16xxx)
    INTEGRATION_FAILED = "INTEGRATION_FAILED"
    INTEGRATION_NOT_FOUND = "INTEGRATION_NOT_FOUND"
    WEBHOOK_FAILED = "WEBHOOK_FAILED"

    # 文档错误 (17xxx)
    DOCUMENTATION_GENERATION_FAILED = "DOCUMENTATION_GENERATION_FAILED"
    DOCUMENTATION_NOT_FOUND = "DOCUMENTATION_NOT_FOUND"

    # 性能优化错误 (18xxx)
    OPTIMIZATION_FAILED = "OPTIMIZATION_FAILED"
    PERFORMANCE_ANALYSIS_FAILED = "PERFORMANCE_ANALYSIS_FAILED"

    # 测试相关错误 (19xxx)
    TEST_EXECUTION_FAILED = "TEST_EXECUTION_FAILED"
    TEST_COVERAGE_ERROR = "TEST_COVERAGE_ERROR"
    TEST_FRAMEWORK_ERROR = "TEST_FRAMEWORK_ERROR"

    # 网络错误 (20xxx)
    NETWORK_ERROR = "NETWORK_ERROR"
    CONNECTION_FAILED = "CONNECTION_FAILED"
    DNS_RESOLUTION_FAILED = "DNS_RESOLUTION_FAILED"

    # 配置错误 (21xxx)
    CONFIG_ERROR = "CONFIG_ERROR"
    CONFIG_NOT_FOUND = "CONFIG_NOT_FOUND"
    CONFIG_VALIDATION_FAILED = "CONFIG_VALIDATION_FAILED"

    # 存储错误 (22xxx)
    STORAGE_ERROR = "STORAGE_ERROR"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    STORAGE_QUOTA_EXCEEDED = "STORAGE_QUOTA_EXCEEDED"

    # 消息队列错误 (23xxx)
    MESSAGE_QUEUE_ERROR = "MESSAGE_QUEUE_ERROR"
    MESSAGE_PUBLISH_FAILED = "MESSAGE_PUBLISH_FAILED"
    MESSAGE_CONSUME_FAILED = "MESSAGE_CONSUME_FAILED"

    # 安全错误 (24xxx)
    SECURITY_VIOLATION = "SECURITY_VIOLATION"
    ENCRYPTION_FAILED = "ENCRYPTION_FAILED"
    DECRYPTION_FAILED = "DECRYPTION_FAILED"

    # 国际化错误 (25xxx)
    I18N_LOCALE_NOT_FOUND = "I18N_LOCALE_NOT_FOUND"
    I18N_TRANSLATION_FAILED = "I18N_TRANSLATION_FAILED"
    I18N_RESOURCE_LOAD_FAILED = "I18N_RESOURCE_LOAD_FAILED"

    # 用户管理错误 (26xxx)
    USER_NOT_FOUND = "USER_NOT_FOUND"
    USER_CREATION_FAILED = "USER_CREATION_FAILED"
    USER_UPDATE_FAILED = "USER_UPDATE_FAILED"
    USER_DELETION_FAILED = "USER_DELETION_FAILED"

    # 审计错误 (27xxx)
    AUDIT_LOG_FAILED = "AUDIT_LOG_FAILED"
    AUDIT_RECORD_NOT_FOUND = "AUDIT_RECORD_NOT_FOUND"

    # 企业功能错误 (28xxx)
    ENTERPRISE_FEATURE_DISABLED = "ENTERPRISE_FEATURE_DISABLED"
    TENANT_NOT_FOUND = "TENANT_NOT_FOUND"
    TENANT_LIMIT_EXCEEDED = "TENANT_LIMIT_EXCEEDED"

    # 资源管理错误 (29xxx)
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    RESOURCE_ALLOCATION_FAILED = "RESOURCE_ALLOCATION_FAILED"
    RESOURCE_DEALLOCATION_FAILED = "RESOURCE_DEALLOCATION_FAILED"


class APIResponse(Generic[T]):
    """统一API响应格式"""

    def __init__(
        self,
        success: bool = True,
        data: Optional[T] = None,
        error: Optional[str] = None,
        error_code: Optional[str] = None,
        message: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.success = success
        self.data = data
        self.error = error
        self.error_code = error_code
        self.message = message
        self.request_id = request_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "success": self.success,
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }

        if self.success:
            result["data"] = self.data
            if self.message:
                result["message"] = self.message
        else:
            result["error"] = self.error
            result["error_code"] = self.error_code
            if self.message:
                result["message"] = self.message

        return result

    @staticmethod
    def success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """创建成功响应"""
        response = APIResponse(success=True, data=data, message=message)
        return response.to_dict()

    @staticmethod
    def error_response(
        error: str, error_code: str = ErrorCode.INTERNAL_ERROR, message: Optional[str] = None
    ) -> Dict[str, Any]:
        """创建错误响应"""
        response: APIResponse = APIResponse(
            success=False, error=error, error_code=error_code, message=message or error
        )
        return response.to_dict()


class PaginationParams:
    """标准化分页参数"""

    def __init__(self, page: int = 1, size: int = 20, max_size: int = 100):
        if page < 1:
            raise ValueError("Page must be >= 1")
        if size < 1:
            raise ValueError("Size must be >= 1")
        if size > max_size:
            raise ValueError(f"Size must be <= {max_size}")

        self.page = page
        self.size = size

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.size


class PaginatedResponse(Generic[T]):
    """分页响应格式"""

    def __init__(
        self, items: List[T], total: int, page: int, size: int, request_id: Optional[str] = None
    ):
        self.items = items
        self.total = total
        self.page = page
        self.size = size
        self.request_id = request_id or str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.total_pages = (total + size - 1) // size
        self.has_next = page < self.total_pages
        self.has_prev = page > 1

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": True,
            "data": {
                "items": self.items,
                "total": self.total,
                "page": self.page,
                "size": self.size,
                "total_pages": self.total_pages,
                "has_next": self.has_next,
                "has_prev": self.has_prev,
            },
            "timestamp": self.timestamp,
            "request_id": self.request_id,
        }


def create_success_response(data: Any = None, message: str = "Success") -> Dict[str, Any]:
    """
    创建成功响应的便捷函数

    Args:
        data: 响应数据
        message: 成功消息

    Returns:
        标准化的成功响应
    """
    return APIResponse.success_response(data, message)


def create_error_response(
    error: str, error_code: str = ErrorCode.INTERNAL_ERROR, message: str = None
) -> Dict[str, Any]:
    """
    创建错误响应的便捷函数

    Args:
        error: 错误信息
        error_code: 错误码
        message: 错误消息

    Returns:
        标准化的错误响应
    """
    return APIResponse.error_response(error, error_code, message)


def create_paginated_response(items: List[Any], total: int, page: int, size: int) -> Dict[str, Any]:
    """
    创建分页响应的便捷函数

    Args:
        items: 数据项列表
        total: 总数量
        page: 当前页码
        size: 每页大小

    Returns:
        标准化的分页响应
    """
    response = PaginatedResponse(items, total, page, size)
    return response.to_dict()


class APIResponseMiddleware:
    """API响应中间件，自动包装JSON响应为标准格式"""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_message: Dict[str, Any] = {}
        body_parts: List[bytes] = []

        async def wrapped_send(message: Dict[str, Any]):
            if message["type"] == "http.response.start":
                start_message.update(message)
                return
            if message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                if message.get("more_body", False):
                    return

            # 如果 body 接收完成，统一包装
            raw_body = b"".join(body_parts)
            body_parts.clear()

            status_code = start_message.get("status", 200)
            headers = {k.decode().lower(): v.decode() for k, v in start_message.get("headers", [])}
            is_json = "application/json" in headers.get("content-type", "")

            if is_json and raw_body:
                try:
                    payload = json.loads(raw_body.decode("utf-8"))
                except Exception:
                    payload = None

                if isinstance(payload, dict) and ("code" in payload or "data" in payload):
                    # 已经包装过的响应，直接透传
                    pass
                elif payload is not None and 200 <= status_code < 300:
                    raw_body = json.dumps(create_success_response(payload),
                                          ensure_ascii=False).encode("utf-8")
                elif payload is not None and status_code >= 400:
                    message_text = payload.get("detail") if isinstance(
                        payload, dict) else str(payload)
                    raw_body = json.dumps(
                        create_error_response("ERROR", f"HTTP {status_code}", message_text), ensure_ascii=False
                    ).encode("utf-8")

            headers_list = list(start_message.get("headers", []))
            # 更新 content-length 如果存在
            for idx, (k, v) in enumerate(headers_list):
                if k.decode().lower() == "content-length":
                    headers_list[idx] = (k, str(len(raw_body)).encode())
                    break

            await send({
                "type": "http.response.start",
                "status": start_message.get("status", 200),
                "headers": headers_list,
            })
            await send({
                "type": "http.response.body",
                "body": raw_body,
                "more_body": False,
            })

        await self.app(scope, receive, wrapped_send)


# 在exception_handler.py中添加对统一响应的支持
def create_http_exception(status_code: int, error_code: str, message: str) -> HTTPException:
    """
    创建HTTP异常的便捷函数

    Args:
        status_code: HTTP状态码
        error_code: 错误码
        message: 错误消息

    Returns:
        HTTPException实例
    """
    return HTTPException(
        status_code=status_code, detail=create_error_response(error_code, error_code, message)
    )
