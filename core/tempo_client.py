# -*- coding: utf-8 -*-
"""
Tempo Client - Real Integration
==============================

真实的Tempo集成客户端，用于查询Tempo分布式追踪系统。
支持追踪查询、Span查询、服务依赖图等功能。

Features:
- Real Tempo API integration
- Trace query
- Span query
- Service dependency graph
- Search traces
- Trace by ID
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TempoSpan(BaseModel):
    """Tempo Span"""

    traceID: str = Field(..., description="追踪ID")
    spanID: str = Field(..., description="Span ID")
    parentSpanID: Optional[str] = Field(None, description="父Span ID")
    operationName: str = Field(..., description="操作名称")
    startTime: str = Field(..., description="开始时间")
    duration: int = Field(..., description="持续时间（纳秒）")
    tags: Dict[str, str] = Field(default_factory=dict, description="标签")
    logs: List[Dict[str, Any]] = Field(default_factory=list, description="日志")
    process: Dict[str, Any] = Field(default_factory=dict, description="进程信息")


class TempoTrace(BaseModel):
    """Tempo追踪"""

    traceID: str = Field(..., description="追踪ID")
    spans: List[TempoSpan] = Field(default_factory=list, description="Span列表")
    processes: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="进程信息")


class TempoSearchResult(BaseModel):
    """Tempo搜索结果"""

    traces: List[Dict[str, Any]] = Field(default_factory=list, description="追踪列表")
    totalTraces: int = Field(default=0, description="总追踪数")
    limit: int = Field(default=0, description="限制数量")
    offset: int = Field(default=0, description="偏移量")


class TempoServiceDependency(BaseModel):
    """Tempo服务依赖"""

    service: str = Field(..., description="服务名称")
    dependencies: List[str] = Field(default_factory=list, description="依赖服务列表")
    call_count: int = Field(default=0, description="调用次数")
    avg_latency_ms: float = Field(default=0.0, description="平均延迟（毫秒）")


class TempoClient:
    """Tempo客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        初始化Tempo客户端

        Args:
            base_url: Tempo服务器URL，默认从环境变量TEMPO_URL读取
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url or os.getenv(
            "TEMPO_URL", "http://localhost:3200"
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # 创建HTTP客户端
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
        )

        logger.info(f"Tempo client initialized with base_url: {self.base_url}")

    async def close(self):
        """关闭HTTP客户端"""
        await self._client.aclose()
        logger.info("Tempo client closed")

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
            logger.error(f"Tempo HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Tempo request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Tempo request failed: {e}")
            raise

    async def search_traces(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 20,
    ) -> TempoSearchResult:
        """
        搜索追踪

        Args:
            query: 搜索查询（Tempo查询语法）
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制

        Returns:
            搜索结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {
            "query": query,
            "start": str(int(start.timestamp() * 1e9)),  # Tempo使用纳秒时间戳
            "end": str(int(end.timestamp() * 1e9)),
            "limit": str(limit),
        }

        logger.info(f"Executing Tempo trace search: {query}")

        try:
            data = await self._request("GET", "/api/search", params=params)

            return TempoSearchResult(
                traces=data.get("traces", []),
                totalTraces=data.get("totalTraces", 0),
                limit=data.get("limit", limit),
                offset=data.get("offset", 0),
            )
        except Exception as e:
            logger.error(f"Tempo trace search error: {e}")
            raise

    async def get_trace(self, trace_id: str) -> TempoTrace:
        """
        根据追踪ID获取追踪

        Args:
            trace_id: 追踪ID

        Returns:
            追踪数据

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info(f"Getting Tempo trace: {trace_id}")

        try:
            data = await self._request("GET", f"/api/traces/{trace_id}")

            # Tempo返回的数据格式: {"data": {"traceID": "...", "spans": [...], ...}}
            trace_data = data.get("data", {})

            return TempoTrace(
                traceID=trace_data.get("traceID", trace_id),
                spans=[TempoSpan(**span) for span in trace_data.get("spans", [])],
                processes=trace_data.get("processes", {}),
            )
        except Exception as e:
            logger.error(f"Get Tempo trace error: {e}")
            raise

    async def search_spans(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        搜索Span

        Args:
            query: 搜索查询
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制

        Returns:
            Span列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {
            "query": query,
            "start": str(int(start.timestamp() * 1e9)),
            "end": str(int(end.timestamp() * 1e9)),
            "limit": str(limit),
        }

        logger.info(f"Executing Tempo span search: {query}")

        try:
            data = await self._request("GET", "/api/search", params=params)

            return data.get("traces", [])
        except Exception as e:
            logger.error(f"Tempo span search error: {e}")
            raise

    async def get_service_dependencies(
        self,
        start: datetime,
        end: datetime,
    ) -> List[TempoServiceDependency]:
        """
        获取服务依赖图

        Args:
            start: 开始时间
            end: 结束时间

        Returns:
            服务依赖列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info("Getting Tempo service dependencies")

        try:
            # 搜索所有追踪
            result = await self.search_traces(
                query="{}",
                start=start,
                end=end,
                limit=1000,
            )

            # 分析服务依赖
            service_deps: Dict[str, Dict[str, Any]] = {}

            for trace in result.traces:
                spans = trace.get("spans", [])
                for span in spans:
                    service = span.get("process", {}).get("serviceName", "unknown")
                    parent_span_id = span.get("parentSpanID")

                    if service not in service_deps:
                        service_deps[service] = {
                            "service": service,
                            "dependencies": set(),
                            "call_count": 0,
                            "total_latency": 0,
                        }

                    service_deps[service]["call_count"] += 1
                    service_deps[service]["total_latency"] += span.get("duration", 0) / 1e6  # 转换为毫秒

                    # 查找父服务
                    if parent_span_id:
                        for parent_span in spans:
                            if parent_span.get("spanID") == parent_span_id:
                                parent_service = parent_span.get("process", {}).get("serviceName", "unknown")
                                if parent_service != service:
                                    service_deps[service]["dependencies"].add(parent_service)

            # 转换为结果格式
            dependencies = []
            for service_data in service_deps.values():
                dependencies.append(
                    TempoServiceDependency(
                        service=service_data["service"],
                        dependencies=list(service_data["dependencies"]),
                        call_count=service_data["call_count"],
                        avg_latency_ms=(
                            service_data["total_latency"] / service_data["call_count"]
                            if service_data["call_count"] > 0
                            else 0
                        ),
                    )
                )

            return dependencies
        except Exception as e:
            logger.error(f"Get Tempo service dependencies error: {e}")
            raise

    async def get_trace_by_service(
        self,
        service_name: str,
        start: datetime,
        end: datetime,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        根据服务名称获取追踪

        Args:
            service_name: 服务名称
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制

        Returns:
            追踪列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        query = f'{{service="{service_name}"}}'

        logger.info(f"Getting Tempo traces by service: {service_name}")

        try:
            result = await self.search_traces(
                query=query,
                start=start,
                end=end,
                limit=limit,
            )

            return result.traces
        except Exception as e:
            logger.error(f"Get Tempo traces by service error: {e}")
            raise

    async def get_trace_count(
        self,
        query: str,
        start: datetime,
        end: datetime,
    ) -> int:
        """
        获取追踪数量

        Args:
            query: 搜索查询
            start: 开始时间
            end: 结束时间

        Returns:
            追踪数量

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info(f"Getting Tempo trace count: {query}")

        try:
            result = await self.search_traces(
                query=query,
                start=start,
                end=end,
                limit=1,
            )

            return result.totalTraces
        except Exception as e:
            logger.error(f"Get Tempo trace count error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            # 尝试搜索一个简单的查询
            end = datetime.now(timezone.utc)
            start = end - timedelta(minutes=5)

            await self.search_traces(
                query="{}",
                start=start,
                end=end,
                limit=1,
            )

            return True
        except Exception as e:
            logger.error(f"Tempo health check failed: {e}")
            return False

    async def get_traces_with_error(
        self,
        start: datetime,
        end: datetime,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取包含错误的追踪

        Args:
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制

        Returns:
            追踪列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        query = '{status="error"}'

        logger.info("Getting Tempo traces with error")

        try:
            result = await self.search_traces(
                query=query,
                start=start,
                end=end,
                limit=limit,
            )

            return result.traces
        except Exception as e:
            logger.error(f"Get Tempo traces with error error: {e}")
            raise

    async def get_slow_traces(
        self,
        threshold_ms: float = 1000,
        start: datetime,
        end: datetime,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        获取慢追踪

        Args:
            threshold_ms: 阈值（毫秒）
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制

        Returns:
            追踪列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info(f"Getting Tempo slow traces (threshold: {threshold_ms}ms)")

        try:
            # 搜索所有追踪，然后过滤慢追踪
            result = await self.search_traces(
                query="{}",
                start=start,
                end=end,
                limit=limit * 10,  # 获取更多结果以便过滤
            )

            # 过滤慢追踪
            slow_traces = []
            for trace in result.traces:
                spans = trace.get("spans", [])
                total_duration = sum(span.get("duration", 0) for span in spans) / 1e6  # 转换为毫秒

                if total_duration >= threshold_ms:
                    slow_traces.append(trace)

                    if len(slow_traces) >= limit:
                        break

            return slow_traces
        except Exception as e:
            logger.error(f"Get Tempo slow traces error: {e}")
            raise


# 全局实例
_tempo_client: Optional[TempoClient] = None


def get_tempo_client() -> TempoClient:
    """
    获取Tempo客户端实例

    Returns:
        Tempo客户端实例
    """
    global _tempo_client

    if _tempo_client is None:
        _tempo_client = TempoClient()

    return _tempo_client


async def close_tempo_client():
    """关闭Tempo客户端"""
    global _tempo_client

    if _tempo_client is not None:
        await _tempo_client.close()
        _tempo_client = None
