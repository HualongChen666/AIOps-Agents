# -*- coding: utf-8 -*-
"""
API Governance Module
API治理模块

提供API生命周期管理，包括版本控制、弃用和退役管理。
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class APIStatus(str, Enum):
    """API状态"""

    ACTIVE = "active"  # 活跃
    DEPRECATED = "deprecated"  # 已弃用
    SUNSET = "sunset"  # 即将退役
    RETIRED = "retired"  # 已退役


@dataclass
class APIEndpoint:
    """API端点"""

    path: str
    method: str
    version: str
    status: APIStatus = APIStatus.ACTIVE
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None
    replacement_path: Optional[str] = None
    description: str = ""
    usage_count: int = 0
    last_used: Optional[datetime] = None


@dataclass
class APIVersion:
    """API版本"""

    version: str
    status: APIStatus
    release_date: datetime
    deprecation_date: Optional[datetime] = None
    sunset_date: Optional[datetime] = None
    retirement_date: Optional[datetime] = None
    endpoints: List[APIEndpoint] = field(default_factory=list)
    description: str = ""


class APIGovernance:
    """API治理"""

    def __init__(self):
        """初始化API治理"""
        self._versions: Dict[str, APIVersion] = {}
        self._endpoints: Dict[str, APIEndpoint] = {}
        self._setup_default_versions()

    def _setup_default_versions(self):
        """设置默认API版本"""
        # v1 API - 当前活跃版本
        v1 = APIVersion(
            version="v1",
            status=APIStatus.ACTIVE,
            release_date=datetime.now(timezone.utc) - timedelta(days=365),
            description="Current stable API version",
        )

        # v1端点
        v1_endpoints = [
            APIEndpoint(
                path="/api/v1/alerts",
                method="GET",
                version="v1",
                status=APIStatus.ACTIVE,
                description="Get alert list",
            ),
            APIEndpoint(
                path="/api/v1/alerts",
                method="POST",
                version="v1",
                status=APIStatus.ACTIVE,
                description="Create new alert",
            ),
            APIEndpoint(
                path="/api/v1/metrics",
                method="GET",
                version="v1",
                status=APIStatus.ACTIVE,
                description="Get metrics",
            ),
        ]

        v1.endpoints = v1_endpoints
        self._versions["v1"] = v1

        # 注册端点
        for endpoint in v1_endpoints:
            self._endpoints[f"{endpoint.method}:{endpoint.path}"] = endpoint

    def register_endpoint(self, endpoint: APIEndpoint):
        """
        注册API端点

        Args:
            endpoint: API端点
        """
        key = f"{endpoint.method}:{endpoint.path}"
        self._endpoints[key] = endpoint
        logger.info(f"Registered API endpoint: {key}")

    def deprecate_endpoint(
        self, path: str, method: str, sunset_date: datetime, replacement_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        弃用API端点

        Args:
            path: 端点路径
            method: HTTP方法
            sunset_date: 退役日期
            replacement_path: 替换端点路径

        Returns:
            操作结果
        """
        key = f"{method}:{path}"

        if key not in self._endpoints:
            return {"status": "error", "error": f"Endpoint not found: {key}"}

        endpoint = self._endpoints[key]
        endpoint.status = APIStatus.DEPRECATED
        endpoint.deprecation_date = datetime.now(timezone.utc)
        endpoint.sunset_date = sunset_date
        endpoint.replacement_path = replacement_path

        logger.warning(f"Deprecated endpoint: {key}, sunset date: {sunset_date}")

        return {
            "status": "success",
            "endpoint": key,
            "deprecation_date": endpoint.deprecation_date.isoformat(),
            "sunset_date": endpoint.sunset_date.isoformat(),
            "replacement": replacement_path,
        }

    def retire_endpoint(self, path: str, method: str) -> Dict[str, Any]:
        """
        退役API端点

        Args:
            path: 端点路径
            method: HTTP方法

        Returns:
            操作结果
        """
        key = f"{method}:{path}"

        if key not in self._endpoints:
            return {"status": "error", "error": f"Endpoint not found: {key}"}

        endpoint = self._endpoints[key]
        endpoint.status = APIStatus.RETIRED
        endpoint.retirement_date = datetime.now(timezone.utc)

        logger.warning(f"Retired endpoint: {key}")

        return {
            "status": "success",
            "endpoint": key,
            "retirement_date": endpoint.retirement_date.isoformat(),
        }

    def record_endpoint_usage(self, path: str, method: str):
        """
        记录端点使用情况

        Args:
            path: 端点路径
            method: HTTP方法
        """
        key = f"{method}:{path}"

        if key in self._endpoints:
            self._endpoints[key].usage_count += 1
            self._endpoints[key].last_used = datetime.now(timezone.utc)

    def check_endpoint_status(self, path: str, method: str) -> Dict[str, Any]:
        """
        检查端点状态

        Args:
            path: 端点路径
            method: HTTP方法

        Returns:
            端点状态信息
        """
        key = f"{method}:{path}"

        if key not in self._endpoints:
            return {"status": "error", "error": f"Endpoint not found: {key}"}

        endpoint = self._endpoints[key]

        result: Dict[str, Any] = {
            "status": endpoint.status.value,
            "path": endpoint.path,
            "method": endpoint.method,
            "version": endpoint.version,
        }

        if endpoint.deprecation_date:
            result["deprecation_date"] = endpoint.deprecation_date.isoformat()
            result["warning"] = "This endpoint is deprecated"

        if endpoint.sunset_date:
            result["sunset_date"] = endpoint.sunset_date.isoformat()
            days_until_sunset = (endpoint.sunset_date - datetime.now(timezone.utc)).days
            result["days_until_sunset"] = days_until_sunset
            result["warning"] = f"This endpoint will be sunset in {days_until_sunset} days"

        if endpoint.replacement_path:
            result["replacement"] = endpoint.replacement_path

        if endpoint.status == APIStatus.RETIRED:
            result["error"] = "This endpoint has been retired"

        return result

    def get_endpoints_by_status(self, status: APIStatus) -> List[APIEndpoint]:
        """
        按状态获取端点列表

        Args:
            status: API状态

        Returns:
            端点列表
        """
        return [ep for ep in self._endpoints.values() if ep.status == status]

    def get_sunset_endpoints(self) -> List[APIEndpoint]:
        """
        获取即将退役的端点

        Returns:
            即将退役的端点列表
        """
        return self.get_endpoints_by_status(APIStatus.SUNSET)

    def get_deprecated_endpoints(self) -> List[APIEndpoint]:
        """
        获取已弃用的端点

        Returns:
            已弃用的端点列表
        """
        return self.get_endpoints_by_status(APIStatus.DEPRECATED)

    def get_usage_stats(self) -> Dict[str, Any]:
        """
        获取使用统计

        Returns:
            使用统计信息
        """
        total_usage = sum(ep.usage_count for ep in self._endpoints.values())

        endpoint_stats: List[Dict[str, Any]] = []
        for key, endpoint in self._endpoints.items():
            endpoint_stats.append(
                {
                    "endpoint": key,
                    "usage_count": endpoint.usage_count,
                    "last_used": endpoint.last_used.isoformat() if endpoint.last_used else None,
                    "status": endpoint.status.value,
                }
            )

        # 按使用量排序
        endpoint_stats.sort(key=lambda x: x["usage_count"] or 0, reverse=True)

        return {
            "total_usage": total_usage,
            "total_endpoints": len(self._endpoints),
            "endpoint_stats": endpoint_stats,
        }

    def get_api_versions(self) -> List[Dict[str, Any]]:
        """
        获取API版本列表

        Returns:
            API版本列表
        """
        versions = []
        for version, api_version in self._versions.items():
            versions.append(
                {
                    "version": version,
                    "status": api_version.status.value,
                    "release_date": api_version.release_date.isoformat(),
                    "deprecation_date": (
                        api_version.deprecation_date.isoformat()
                        if api_version.deprecation_date
                        else None
                    ),
                    "sunset_date": (
                        api_version.sunset_date.isoformat() if api_version.sunset_date else None
                    ),
                    "description": api_version.description,
                    "endpoint_count": len(api_version.endpoints),
                }
            )

        return versions


# 全局API治理实例
api_governance = APIGovernance()


async def setup_api_governance():
    """
    设置API治理

    Returns:
        设置结果
    """
    try:
        logger.info("API governance setup completed")

        return {
            "status": "success",
            "versions": len(api_governance.get_api_versions()),
            "endpoints": len(api_governance._endpoints),
        }

    except Exception as e:
        logger.error(f"API governance setup failed: {e}")
        return {"status": "error", "error": str(e)}
