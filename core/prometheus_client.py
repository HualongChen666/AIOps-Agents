# -*- coding: utf-8 -*-
"""
Prometheus Client - Real Integration
=====================================

真实的Prometheus集成客户端，用于查询Prometheus时序数据库。
支持PromQL查询、指标查询、元数据查询等功能。

Features:
- Real Prometheus API integration
- PromQL query support
- Metric metadata query
- Label values query
- Series query
- Range query
- Instant query
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class PrometheusQueryResult(BaseModel):
    """Prometheus查询结果"""

    status: str = Field(..., description="查询状态: success or error")
    data: Dict[str, Any] = Field(..., description="查询数据")
    error_type: Optional[str] = Field(None, description="错误类型")
    error: Optional[str] = Field(None, description="错误信息")


class PrometheusMetric(BaseModel):
    """Prometheus指标"""

    metric: Dict[str, str] = Field(..., description="指标标签")
    value: List[Any] = Field(..., description="指标值 [timestamp, value]")
    histogram: Optional[List[Dict[str, Any]]] = Field(None, description="直方图数据")


class PrometheusTarget(BaseModel):
    """Prometheus目标"""

    labels: Dict[str, str] = Field(..., description="目标标签")
    health: str = Field(..., description="健康状态: up or down")
    last_scrape: str = Field(..., description="最后抓取时间")
    scrape_interval: str = Field(..., description="抓取间隔")
    scrape_timeout: str = Field(..., description="抓取超时")


class PrometheusClient:
    """Prometheus客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        初始化Prometheus客户端

        Args:
            base_url: Prometheus服务器URL，默认从环境变量PROMETHEUS_URL读取
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url or os.getenv(
            "PROMETHEUS_URL", "http://localhost:9090"
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # 创建HTTP客户端
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
        )

        logger.info(f"Prometheus client initialized with base_url: {self.base_url}")

    async def close(self):
        """关闭HTTP客户端"""
        await self._client.aclose()
        logger.info("Prometheus client closed")

    def _build_url(self, endpoint: str) -> str:
        """
        构建完整的API URL

        Args:
            endpoint: API端点

        Returns:
            完整的URL
        """
        return urljoin(self.base_url, endpoint)

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        发送HTTP请求

        Args:
            method: HTTP方法
            endpoint: API端点
            params: 查询参数
            json_data: JSON数据

        Returns:
            响应数据

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 响应数据格式错误
        """
        url = self._build_url(endpoint)

        try:
            response = await self._client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
            )

            response.raise_for_status()
            data = response.json()

            return data
        except httpx.HTTPStatusError as e:
            logger.error(f"Prometheus HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Prometheus request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Prometheus request failed: {e}")
            raise

    async def query(
        self,
        query: str,
        time: Optional[datetime] = None,
        timeout: Optional[str] = None,
    ) -> PrometheusQueryResult:
        """
        执行即时查询（Instant Query）

        Args:
            query: PromQL查询语句
            time: 查询时间点，默认为当前时间
            timeout: 查询超时时间

        Returns:
            查询结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {"query": query}

        if time:
            params["time"] = str(int(time.timestamp()))
        if timeout:
            params["timeout"] = timeout

        logger.info(f"Executing Prometheus instant query: {query}")

        try:
            data = await self._request("GET", "/api/v1/query", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                error_type = data.get("errorType", "Unknown")
                logger.error(f"Prometheus query failed: {error_type} - {error_msg}")
                raise ValueError(f"Prometheus query failed: {error_msg}")

            return PrometheusQueryResult(**data)
        except Exception as e:
            logger.error(f"Prometheus instant query error: {e}")
            raise

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
        timeout: Optional[str] = None,
    ) -> PrometheusQueryResult:
        """
        执行范围查询（Range Query）

        Args:
            query: PromQL查询语句
            start: 开始时间
            end: 结束时间
            step: 查询步长（如: 1m, 5m, 1h）
            timeout: 查询超时时间

        Returns:
            查询结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {
            "query": query,
            "start": str(int(start.timestamp())),
            "end": str(int(end.timestamp())),
            "step": step,
        }

        if timeout:
            params["timeout"] = timeout

        logger.info(
            f"Executing Prometheus range query: {query} from {start} to {end} step={step}"
        )

        try:
            data = await self._request("GET", "/api/v1/query_range", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                error_type = data.get("errorType", "Unknown")
                logger.error(f"Prometheus range query failed: {error_type} - {error_msg}")
                raise ValueError(f"Prometheus range query failed: {error_msg}")

            return PrometheusQueryResult(**data)
        except Exception as e:
            logger.error(f"Prometheus range query error: {e}")
            raise

    async def query_series(
        self,
        match: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """
        查询时间序列（Series Query）

        Args:
            match: 匹配器列表，如: ['up', 'process_cpu_seconds_total']
            start: 开始时间
            end: 结束时间

        Returns:
            时间序列列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {"match[]": match}

        if start:
            params["start"] = str(int(start.timestamp()))
        if end:
            params["end"] = str(int(end.timestamp()))

        logger.info(f"Executing Prometheus series query: {match}")

        try:
            data = await self._request("GET", "/api/v1/series", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Prometheus series query failed: {error_msg}")
                raise ValueError(f"Prometheus series query failed: {error_msg}")

            return data.get("data", [])
        except Exception as e:
            logger.error(f"Prometheus series query error: {e}")
            raise

    async def query_labels(
        self,
        label_name: Optional[str] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[str]:
        """
        查询标签名或标签值（Labels Query）

        Args:
            label_name: 标签名，如果为None则查询所有标签名
            start: 开始时间
            end: 结束时间

        Returns:
            标签名或标签值列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {}

        if label_name:
            endpoint = f"/api/v1/label/{label_name}/values"
        else:
            endpoint = "/api/v1/labels"

        if start:
            params["start"] = str(int(start.timestamp()))
        if end:
            params["end"] = str(int(end.timestamp()))

        logger.info(f"Executing Prometheus labels query: {label_name or 'all labels'}")

        try:
            data = await self._request("GET", endpoint, params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Prometheus labels query failed: {error_msg}")
                raise ValueError(f"Prometheus labels query failed: {error_msg}")

            return data.get("data", [])
        except Exception as e:
            logger.error(f"Prometheus labels query error: {e}")
            raise

    async def query_targets(self) -> Dict[str, Any]:
        """
        查询Prometheus目标（Targets Query）

        Returns:
            目标信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info("Executing Prometheus targets query")

        try:
            data = await self._request("GET", "/api/v1/targets")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Prometheus targets query failed: {error_msg}")
                raise ValueError(f"Prometheus targets query failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Prometheus targets query error: {e}")
            raise

    async def query_metadata(
        self,
        metric: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        查询指标元数据（Metadata Query）

        Args:
            metric: 指标名称，如果为None则查询所有指标
            limit: 返回结果数量限制

        Returns:
            指标元数据

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {}

        if metric:
            params["metric"] = metric
        if limit:
            params["limit"] = str(limit)

        logger.info(f"Executing Prometheus metadata query: {metric or 'all metrics'}")

        try:
            data = await self._request("GET", "/api/v1/metadata", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Prometheus metadata query failed: {error_msg}")
                raise ValueError(f"Prometheus metadata query failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Prometheus metadata query error: {e}")
            raise

    async def get_config(self) -> Dict[str, Any]:
        """
        获取Prometheus配置

        Returns:
            Prometheus配置

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Prometheus configuration")

        try:
            data = await self._request("GET", "/api/v1/config")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Get Prometheus config failed: {error_msg}")
                raise ValueError(f"Get Prometheus config failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Get Prometheus config error: {e}")
            raise

    async def get_runtime_info(self) -> Dict[str, Any]:
        """
        获取Prometheus运行时信息

        Returns:
            运行时信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Prometheus runtime info")

        try:
            data = await self._request("GET", "/api/v1/status/runtimeinfo")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Get Prometheus runtime info failed: {error_msg}")
                raise ValueError(f"Get Prometheus runtime info failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Get Prometheus runtime info error: {e}")
            raise

    async def get_build_info(self) -> Dict[str, Any]:
        """
        获取Prometheus构建信息

        Returns:
            构建信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Prometheus build info")

        try:
            data = await self._request("GET", "/api/v1/status/buildinfo")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Get Prometheus build info failed: {error_msg}")
                raise ValueError(f"Get Prometheus build info failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Get Prometheus build info error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            await self.get_build_info()
            return True
        except Exception as e:
            logger.error(f"Prometheus health check failed: {e}")
            return False

    async def get_cpu_usage(self, time_range: str = "1h") -> List[float]:
        """
        获取CPU使用率

        Args:
            time_range: 时间范围 (1h, 24h, 7d)

        Returns:
            CPU使用率列表
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168)

            result = await self.query_range(
                query='100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)',
                start=start,
                end=end,
                step="1m",
            )

            # 提取CPU使用率数据
            cpu_values = []
            if result.data.get("resultType") == "matrix":
                for result_item in result.data.get("result", []):
                    for value in result_item.get("values", []):
                        cpu_values.append(float(value[1]))

            return cpu_values
        except Exception as e:
            logger.error(f"Get CPU usage failed: {e}")
            return []

    async def get_memory_usage(self, time_range: str = "1h") -> List[float]:
        """
        获取内存使用率

        Args:
            time_range: 时间范围 (1h, 24h, 7d)

        Returns:
            内存使用率列表
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168)

            result = await self.query_range(
                query='(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100',
                start=start,
                end=end,
                step="1m",
            )

            # 提取内存使用率数据
            memory_values = []
            if result.data.get("resultType") == "matrix":
                for result_item in result.data.get("result", []):
                    for value in result_item.get("values", []):
                        memory_values.append(float(value[1]))

            return memory_values
        except Exception as e:
            logger.error(f"Get memory usage failed: {e}")
            return []

    async def get_disk_usage(self, time_range: str = "1h") -> List[float]:
        """
        获取磁盘使用率

        Args:
            time_range: 时间范围 (1h, 24h, 7d)

        Returns:
            磁盘使用率列表
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168)

            result = await self.query_range(
                query='(1 - (node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"})) * 100',
                start=start,
                end=end,
                step="1m",
            )

            # 提取磁盘使用率数据
            disk_values = []
            if result.data.get("resultType") == "matrix":
                for result_item in result.data.get("result", []):
                    for value in result_item.get("values", []):
                        disk_values.append(float(value[1]))

            return disk_values
        except Exception as e:
            logger.error(f"Get disk usage failed: {e}")
            return []


# 全局实例
_prometheus_client: Optional[PrometheusClient] = None


def get_prometheus_client() -> PrometheusClient:
    """
    获取Prometheus客户端实例

    Returns:
        Prometheus客户端实例
    """
    global _prometheus_client

    if _prometheus_client is None:
        _prometheus_client = PrometheusClient()

    return _prometheus_client


async def close_prometheus_client():
    """关闭Prometheus客户端"""
    global _prometheus_client

    if _prometheus_client is not None:
        await _prometheus_client.close()
        _prometheus_client = None
