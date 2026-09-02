# -*- coding: utf-8 -*-
"""
Loki Client - Real Integration
==============================

真实的Loki集成客户端，用于查询Loki日志聚合系统。
支持LogQL查询、标签查询、流查询等功能。

Features:
- Real Loki API integration
- LogQL query support
- Label query
- Stream query
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


class LokiStream(BaseModel):
    """Loki流"""

    stream: Dict[str, str] = Field(..., description="流标签")
    values: List[List[str]] = Field(..., description="日志值 [[timestamp, message], ...]")


class LokiQueryResult(BaseModel):
    """Loki查询结果"""

    status: str = Field(..., description="查询状态: success or error")
    data: Dict[str, Any] = Field(..., description="查询数据")
    error_type: Optional[str] = Field(None, description="错误类型")
    error: Optional[str] = Field(None, description="错误信息")


class LokiLabelResponse(BaseModel):
    """Loki标签响应"""

    status: str = Field(..., description="查询状态")
    data: List[str] = Field(..., description="标签列表")


class LokiClient:
    """Loki客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        初始化Loki客户端

        Args:
            base_url: Loki服务器URL，默认从环境变量LOKI_URL读取
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url or os.getenv(
            "LOKI_URL", "http://localhost:3100"
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # 创建HTTP客户端
        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
        )

        logger.info(f"Loki client initialized with base_url: {self.base_url}")

    async def close(self):
        """关闭HTTP客户端"""
        await self._client.aclose()
        logger.info("Loki client closed")

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
            logger.error(f"Loki HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Loki request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Loki request failed: {e}")
            raise

    async def query(
        self,
        query: str,
        limit: int = 100,
        time: Optional[datetime] = None,
        direction: str = "backward",
    ) -> LokiQueryResult:
        """
        执行即时查询（Instant Query）

        Args:
            query: LogQL查询语句
            limit: 返回结果数量限制
            time: 查询时间点，默认为当前时间
            direction: 查询方向 (forward or backward)

        Returns:
            查询结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {
            "query": query,
            "limit": str(limit),
            "direction": direction,
        }

        if time:
            params["time"] = str(int(time.timestamp() * 1e9))  # Loki使用纳秒时间戳

        logger.info(f"Executing Loki instant query: {query}")

        try:
            data = await self._request("GET", "/loki/api/v1/query", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Loki query failed: {error_msg}")
                raise ValueError(f"Loki query failed: {error_msg}")

            return LokiQueryResult(**data)
        except Exception as e:
            logger.error(f"Loki instant query error: {e}")
            raise

    async def query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        limit: int = 100,
        step: str = "1h",
        direction: str = "backward",
    ) -> LokiQueryResult:
        """
        执行范围查询（Range Query）

        Args:
            query: LogQL查询语句
            start: 开始时间
            end: 结束时间
            limit: 返回结果数量限制
            step: 查询步长（如: 1h, 30m）
            direction: 查询方向 (forward or backward)

        Returns:
            查询结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {
            "query": query,
            "start": str(int(start.timestamp() * 1e9)),  # Loki使用纳秒时间戳
            "end": str(int(end.timestamp() * 1e9)),
            "limit": str(limit),
            "step": step,
            "direction": direction,
        }

        logger.info(
            f"Executing Loki range query: {query} from {start} to {end} step={step}"
        )

        try:
            data = await self._request("GET", "/loki/api/v1/query_range", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Loki range query failed: {error_msg}")
                raise ValueError(f"Loki range query failed: {error_msg}")

            return LokiQueryResult(**data)
        except Exception as e:
            logger.error(f"Loki range query error: {e}")
            raise

    async def query_labels(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[str]:
        """
        查询所有标签名（Labels Query）

        Args:
            start: 开始时间
            end: 结束时间

        Returns:
            标签名列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {}

        if start:
            params["start"] = str(int(start.timestamp() * 1e9))
        if end:
            params["end"] = str(int(end.timestamp() * 1e9))

        logger.info("Executing Loki labels query")

        try:
            data = await self._request("GET", "/loki/api/v1/labels", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Loki labels query failed: {error_msg}")
                raise ValueError(f"Loki labels query failed: {error_msg}")

            return data.get("data", [])
        except Exception as e:
            logger.error(f"Loki labels query error: {e}")
            raise

    async def query_label_values(
        self,
        label_name: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[str]:
        """
        查询标签值（Label Values Query）

        Args:
            label_name: 标签名
            start: 开始时间
            end: 结束时间

        Returns:
            标签值列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {}

        if start:
            params["start"] = str(int(start.timestamp() * 1e9))
        if end:
            params["end"] = str(int(end.timestamp() * 1e9))

        logger.info(f"Executing Loki label values query: {label_name}")

        try:
            data = await self._request(
                "GET", f"/loki/api/v1/label/{label_name}/values", params=params
            )

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Loki label values query failed: {error_msg}")
                raise ValueError(f"Loki label values query failed: {error_msg}")

            return data.get("data", [])
        except Exception as e:
            logger.error(f"Loki label values query error: {e}")
            raise

    async def query_series(
        self,
        match: List[str],
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, str]]:
        """
        查询流（Series Query）

        Args:
            match: 匹配器列表，如: ['{job="varlogs"}']
            start: 开始时间
            end: 结束时间

        Returns:
            流列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        params: Dict[str, Any] = {"match[]": match}

        if start:
            params["start"] = str(int(start.timestamp() * 1e9))
        if end:
            params["end"] = str(int(end.timestamp() * 1e9))

        logger.info(f"Executing Loki series query: {match}")

        try:
            data = await self._request("GET", "/loki/api/v1/series", params=params)

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Loki series query failed: {error_msg}")
                raise ValueError(f"Loki series query failed: {error_msg}")

            return data.get("data", [])
        except Exception as e:
            logger.error(f"Loki series query error: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """
        获取Loki统计信息

        Returns:
            统计信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Loki stats")

        try:
            data = await self._request("GET", "/loki/api/v1/stats")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Get Loki stats failed: {error_msg}")
                raise ValueError(f"Get Loki stats failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Get Loki stats error: {e}")
            raise

    async def get_config(self) -> Dict[str, Any]:
        """
        获取Loki配置

        Returns:
            Loki配置

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Loki config")

        try:
            data = await self._request("GET", "/loki/api/v1/config")

            if data.get("status") != "success":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Get Loki config failed: {error_msg}")
                raise ValueError(f"Get Loki config failed: {error_msg}")

            return data.get("data", {})
        except Exception as e:
            logger.error(f"Get Loki config error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            await self.get_config()
            return True
        except Exception as e:
            logger.error(f"Loki health check failed: {e}")
            return False

    async def search_logs(
        self,
        query: str,
        time_range: str = "1h",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        搜索日志

        Args:
            query: LogQL查询语句
            time_range: 时间范围 (1h, 24h, 7d)
            limit: 返回结果数量限制

        Returns:
            日志列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(
                hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168
            )

            result = await self.query_range(
                query=query,
                start=start,
                end=end,
                limit=limit,
                step="1h",
            )

            # 提取日志数据
            logs = []
            if result.data.get("resultType") == "streams":
                for stream in result.data.get("result", []):
                    stream_labels = stream.get("stream", {})
                    for value in stream.get("values", []):
                        timestamp_ns = value[0]
                        message = value[1]
                        timestamp = datetime.fromtimestamp(
                            int(timestamp_ns) / 1e9, tz=timezone.utc
                        )

                        logs.append(
                            {
                                "timestamp": timestamp.isoformat(),
                                "message": message,
                                "labels": stream_labels,
                            }
                        )

            return logs
        except Exception as e:
            logger.error(f"Search logs failed: {e}")
            return []

    async def get_error_logs(
        self,
        time_range: str = "1h",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取错误日志

        Args:
            time_range: 时间范围 (1h, 24h, 7d)
            limit: 返回结果数量限制

        Returns:
            错误日志列表
        """
        return await self.search_logs(
            query='{level="error"} |= ""',
            time_range=time_range,
            limit=limit,
        )

    async def get_warning_logs(
        self,
        time_range: str = "1h",
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        获取警告日志

        Args:
            time_range: 时间范围 (1h, 24h, 7d)
            limit: 返回结果数量限制

        Returns:
            警告日志列表
        """
        return await self.search_logs(
            query='{level="warning"} |= ""',
            time_range=time_range,
            limit=limit,
        )

    async def count_logs(
        self,
        query: str,
        time_range: str = "1h",
    ) -> int:
        """
        统计日志数量

        Args:
            query: LogQL查询语句
            time_range: 时间范围 (1h, 24h, 7d)

        Returns:
            日志数量
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(
                hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168
            )

            result = await self.query_range(
                query=f'count_over_time({query})',
                start=start,
                end=end,
                limit=1,
                step="1h",
            )

            # 提取日志数量
            count = 0
            if result.data.get("resultType") == "matrix":
                for result_item in result.data.get("result", []):
                    for value in result_item.get("values", []):
                        count += int(float(value[1]))

            return count
        except Exception as e:
            logger.error(f"Count logs failed: {e}")
            return 0


# 全局实例
_loki_client: Optional[LokiClient] = None


def get_loki_client() -> LokiClient:
    """
    获取Loki客户端实例

    Returns:
        Loki客户端实例
    """
    global _loki_client

    if _loki_client is None:
        _loki_client = LokiClient()

    return _loki_client


async def close_loki_client():
    """关闭Loki客户端"""
    global _loki_client

    if _loki_client is not None:
        await _loki_client.close()
        _loki_client = None
