# -*- coding: utf-8 -*-
"""
Elasticsearch Client - Real Integration
=======================================

真实的Elasticsearch集成客户端，用于查询Elasticsearch日志搜索引擎。
支持全文搜索、聚合查询、索引管理等功能。

Features:
- Real Elasticsearch API integration
- Full-text search
- Aggregation queries
- Index management
- Document CRUD operations
- Bulk operations
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ElasticsearchHit(BaseModel):
    """Elasticsearch文档命中"""

    index: str = Field(..., alias="_index", description="索引名称")
    id: str = Field(..., alias="_id", description="文档ID")
    score: float = Field(..., alias="_score", description="相关性得分")
    source: Dict[str, Any] = Field(..., alias="_source", description="文档源数据")


class ElasticsearchSearchResult(BaseModel):
    """Elasticsearch搜索结果"""

    took: int = Field(..., description="查询耗时（毫秒）")
    timed_out: bool = Field(..., description="是否超时")
    shards: Dict[str, Any] = Field(..., alias="_shards", description="分片信息")
    hits: Dict[str, Any] = Field(..., description="命中结果")
    total: int = Field(default=0, description="总命中数")


class ElasticsearchIndex(BaseModel):
    """Elasticsearch索引"""

    index: str = Field(..., description="索引名称")
    health: str = Field(..., description="健康状态")
    status: str = Field(..., description="状态")
    docs_count: int = Field(default=0, description="文档数量")
    store_size: str = Field(default="0b", description="存储大小")


class ElasticsearchClient:
    """Elasticsearch客户端"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        timeout: int = 30,
        verify_ssl: bool = True,
    ):
        """
        初始化Elasticsearch客户端

        Args:
            base_url: Elasticsearch服务器URL，默认从环境变量ELASTICSEARCH_URL读取
            username: 用户名，默认从环境变量ELASTICSEARCH_USERNAME读取
            password: 密码，默认从环境变量ELASTICSEARCH_PASSWORD读取
            timeout: 请求超时时间（秒）
            verify_ssl: 是否验证SSL证书
        """
        self.base_url = base_url or os.getenv(
            "ELASTICSEARCH_URL", "http://localhost:9200"
        )
        self.username = username or os.getenv("ELASTICSEARCH_USERNAME", None)
        self.password = password or os.getenv("ELASTICSEARCH_PASSWORD", None)
        self.timeout = timeout
        self.verify_ssl = verify_ssl

        # 创建HTTP客户端
        headers = {}
        if self.username and self.password:
            import base64

            auth_str = f"{self.username}:{self.password}"
            b64_auth = base64.b64encode(auth_str.encode()).decode()
            headers["Authorization"] = f"Basic {b64_auth}"

        self._client = httpx.AsyncClient(
            timeout=timeout,
            verify=verify_ssl,
            headers=headers,
        )

        logger.info(f"Elasticsearch client initialized with base_url: {self.base_url}")

    async def close(self):
        """关闭HTTP客户端"""
        await self._client.aclose()
        logger.info("Elasticsearch client closed")

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
            logger.error(f"Elasticsearch HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Elasticsearch request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Elasticsearch request failed: {e}")
            raise

    async def search(
        self,
        index: str,
        query: Dict[str, Any],
        size: int = 10,
        from_: int = 0,
        sort: Optional[List[str]] = None,
    ) -> ElasticsearchSearchResult:
        """
        执行搜索查询

        Args:
            index: 索引名称或模式
            query: 查询DSL
            size: 返回结果数量
            from_: 偏移量
            sort: 排序字段

        Returns:
            搜索结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        body: Dict[str, Any] = {
            "query": query,
            "size": size,
            "from": from_,
        }

        if sort:
            body["sort"] = sort

        logger.info(f"Executing Elasticsearch search on index: {index}")

        try:
            data = await self._request("POST", f"/{index}/_search", json_data=body)

            return ElasticsearchSearchResult(**data)
        except Exception as e:
            logger.error(f"Elasticsearch search error: {e}")
            raise

    async def search_logs(
        self,
        index: str,
        query_string: str,
        time_range: str = "1h",
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        搜索日志

        Args:
            index: 索引名称或模式
            query_string: 查询字符串
            time_range: 时间范围 (1h, 24h, 7d)
            size: 返回结果数量

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

            query = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "query_string": {
                                    "query": query_string,
                                }
                            },
                            {
                                "range": {
                                    "@timestamp": {
                                        "gte": start.isoformat(),
                                        "lte": end.isoformat(),
                                    }
                                }
                            },
                        ]
                    }
                }
            }

            result = await self.search(
                index=index,
                query=query,
                size=size,
                sort=["@timestamp:desc"],
            )

            # 提取日志数据
            logs = []
            for hit in result.hits.get("hits", []):
                logs.append(
                    {
                        "_id": hit.get("_id"),
                        "_index": hit.get("_index"),
                        "_score": hit.get("_score"),
                        "timestamp": hit.get("_source", {}).get("@timestamp"),
                        "level": hit.get("_source", {}).get("level"),
                        "message": hit.get("_source", {}).get("message"),
                        "service": hit.get("_source", {}).get("service"),
                        "source": hit.get("_source", {}),
                    }
                )

            return logs
        except Exception as e:
            logger.error(f"Search logs error: {e}")
            raise

    async def aggregate(
        self,
        index: str,
        aggs: Dict[str, Any],
        query: Optional[Dict[str, Any]] = None,
        size: int = 0,
    ) -> Dict[str, Any]:
        """
        执行聚合查询

        Args:
            index: 索引名称或模式
            aggs: 聚合DSL
            query: 查询DSL
            size: 返回结果数量

        Returns:
            聚合结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        body: Dict[str, Any] = {
            "aggs": aggs,
            "size": size,
        }

        if query:
            body["query"] = query

        logger.info(f"Executing Elasticsearch aggregation on index: {index}")

        try:
            data = await self._request("POST", f"/{index}/_search", json_data=body)

            return data.get("aggregations", {})
        except Exception as e:
            logger.error(f"Elasticsearch aggregation error: {e}")
            raise

    async def get_index(self, index: str) -> Dict[str, Any]:
        """
        获取索引信息

        Args:
            index: 索引名称

        Returns:
            索引信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info(f"Getting Elasticsearch index: {index}")

        try:
            data = await self._request("GET", f"/{index}")

            return data.get(index, {})
        except Exception as e:
            logger.error(f"Get Elasticsearch index error: {e}")
            raise

    async def get_indices(self) -> List[str]:
        """
        获取所有索引名称

        Returns:
            索引名称列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Elasticsearch indices")

        try:
            data = await self._request("GET", "/_cat/indices?format=json")

            indices = [index.get("index") for index in data if index.get("index")]

            return indices
        except Exception as e:
            logger.error(f"Get Elasticsearch indices error: {e}")
            raise

    async def get_cluster_info(self) -> Dict[str, Any]:
        """
        获取集群信息

        Returns:
            集群信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Elasticsearch cluster info")

        try:
            data = await self._request("GET", "/")

            return data
        except Exception as e:
            logger.error(f"Get Elasticsearch cluster info error: {e}")
            raise

    async def get_cluster_health(self) -> Dict[str, Any]:
        """
        获取集群健康状态

        Returns:
            集群健康状态

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Elasticsearch cluster health")

        try:
            data = await self._request("GET", "/_cluster/health")

            return data
        except Exception as e:
            logger.error(f"Get Elasticsearch cluster health error: {e}")
            raise

    async def get_cluster_stats(self) -> Dict[str, Any]:
        """
        获取集群统计信息

        Returns:
            集群统计信息

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info("Getting Elasticsearch cluster stats")

        try:
            data = await self._request("GET", "/_cluster/stats")

            return data
        except Exception as e:
            logger.error(f"Get Elasticsearch cluster stats error: {e}")
            raise

    async def count(
        self,
        index: str,
        query: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        统计文档数量

        Args:
            index: 索引名称或模式
            query: 查询DSL

        Returns:
            文档数量

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        logger.info(f"Counting documents in index: {index}")

        try:
            if query:
                data = await self._request("POST", f"/{index}/_count", json_data={"query": query})
            else:
                data = await self._request("GET", f"/{index}/_count")

            return data.get("count", 0)
        except Exception as e:
            logger.error(f"Count documents error: {e}")
            raise

    async def get_document(
        self,
        index: str,
        doc_id: str,
    ) -> Dict[str, Any]:
        """
        获取文档

        Args:
            index: 索引名称
            doc_id: 文档ID

        Returns:
            文档数据

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 获取失败
        """
        logger.info(f"Getting document: {index}/{doc_id}")

        try:
            data = await self._request("GET", f"/{index}/_doc/{doc_id}")

            return data
        except Exception as e:
            logger.error(f"Get document error: {e}")
            raise

    async def index_document(
        self,
        index: str,
        doc_id: Optional[str],
        document: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        索引文档

        Args:
            index: 索引名称
            doc_id: 文档ID（可选）
            document: 文档数据

        Returns:
            索引结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 索引失败
        """
        logger.info(f"Indexing document in: {index}")

        try:
            if doc_id:
                data = await self._request("PUT", f"/{index}/_doc/{doc_id}", json_data=document)
            else:
                data = await self._request("POST", f"/{index}/_doc", json_data=document)

            return data
        except Exception as e:
            logger.error(f"Index document error: {e}")
            raise

    async def delete_document(
        self,
        index: str,
        doc_id: str,
    ) -> Dict[str, Any]:
        """
        删除文档

        Args:
            index: 索引名称
            doc_id: 文档ID

        Returns:
            删除结果

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 删除失败
        """
        logger.info(f"Deleting document: {index}/{doc_id}")

        try:
            data = await self._request("DELETE", f"/{index}/_doc/{doc_id}")

            return data
        except Exception as e:
            logger.error(f"Delete document error: {e}")
            raise

    async def health_check(self) -> bool:
        """
        健康检查

        Returns:
            是否健康
        """
        try:
            health = await self.get_cluster_health()
            return health.get("status") in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Elasticsearch health check failed: {e}")
            return False

    async def get_error_logs(
        self,
        index: str,
        time_range: str = "1h",
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取错误日志

        Args:
            index: 索引名称或模式
            time_range: 时间范围 (1h, 24h, 7d)
            size: 返回结果数量

        Returns:
            错误日志列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        return await self.search_logs(
            index=index,
            query_string='level:ERROR OR level:error',
            time_range=time_range,
            size=size,
        )

    async def get_log_patterns(
        self,
        index: str,
        time_range: str = "1h",
        size: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        获取日志模式（使用terms聚合）

        Args:
            index: 索引名称或模式
            time_range: 时间范围 (1h, 24h, 7d)
            size: 返回结果数量

        Returns:
            日志模式列表

        Raises:
            httpx.HTTPError: HTTP请求失败
            ValueError: 查询失败
        """
        try:
            end = datetime.now(timezone.utc)
            start = end - timedelta(
                hours=1 if time_range == "1h" else 24 if time_range == "24h" else 168
            )

            query = {
                "range": {
                    "@timestamp": {
                        "gte": start.isoformat(),
                        "lte": end.isoformat(),
                    }
                }
            }

            aggs = {
                "log_patterns": {
                    "terms": {
                        "field": "message.keyword",
                        "size": size,
                    }
                }
            }

            result = await self.aggregate(
                index=index,
                aggs=aggs,
                query=query,
            )

            # 提取日志模式
            patterns = []
            for bucket in result.get("log_patterns", {}).get("buckets", []):
                patterns.append(
                    {
                        "pattern": bucket.get("key"),
                        "count": bucket.get("doc_count"),
                    }
                )

            return patterns
        except Exception as e:
            logger.error(f"Get log patterns error: {e}")
            raise


# 全局实例
_elasticsearch_client: Optional[ElasticsearchClient] = None


def get_elasticsearch_client() -> ElasticsearchClient:
    """
    获取Elasticsearch客户端实例

    Returns:
        Elasticsearch客户端实例
    """
    global _elasticsearch_client

    if _elasticsearch_client is None:
        _elasticsearch_client = ElasticsearchClient()

    return _elasticsearch_client


async def close_elasticsearch_client():
    """关闭Elasticsearch客户端"""
    global _elasticsearch_client

    if _elasticsearch_client is not None:
        await _elasticsearch_client.close()
        _elasticsearch_client = None
