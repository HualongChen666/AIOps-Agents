# -*- coding: utf-8 -*-
"""
Unit Tests for Monitoring Clients
==================================

Tests for Prometheus, Loki, Tempo, and Elasticsearch clients.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta, timezone

from core.prometheus_client import PrometheusClient, PrometheusQueryResult
from core.loki_client import LokiClient, LokiQueryResult
from core.tempo_client import TempoClient, TempoSearchResult
from core.elasticsearch_client import ElasticsearchClient, ElasticsearchSearchResult


class TestPrometheusClient:
    """Prometheus客户端测试"""

    @pytest.fixture
    def prometheus_client(self):
        """创建Prometheus客户端实例"""
        return PrometheusClient(base_url="http://localhost:9090")

    @pytest.mark.asyncio
    async def test_query_instant(self, prometheus_client):
        """测试即时查询"""
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "vector",
                "result": [
                    {
                        "metric": {"__name__": "up", "job": "prometheus"},
                        "value": [1234567890, "1"],
                    }
                ],
            },
        }

        with patch.object(prometheus_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await prometheus_client.query(query="up")

            assert result.status == "success"
            assert result.data["resultType"] == "vector"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_range(self, prometheus_client):
        """测试范围查询"""
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "up", "job": "prometheus"},
                        "values": [[1234567890, "1"], [1234567950, "1"]],
                    }
                ],
            },
        }

        with patch.object(prometheus_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            start = datetime.now(timezone.utc) - timedelta(hours=1)
            end = datetime.now(timezone.utc)

            result = await prometheus_client.query_range(
                query="up", start=start, end=end, step="1m"
            )

            assert result.status == "success"
            assert result.data["resultType"] == "matrix"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_cpu_usage(self, prometheus_client):
        """测试获取CPU使用率"""
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"instance": "localhost"},
                        "values": [[1234567890, "45.5"], [1234567950, "46.2"]],
                    }
                ],
            },
        }

        with patch.object(prometheus_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            cpu_values = await prometheus_client.get_cpu_usage(time_range="1h")

            assert len(cpu_values) > 0
            assert all(isinstance(v, float) for v in cpu_values)

    @pytest.mark.asyncio
    async def test_health_check(self, prometheus_client):
        """测试健康检查"""
        with patch.object(prometheus_client, "get_build_info", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"version": "2.45.0"}

            result = await prometheus_client.health_check()

            assert result is True
            mock_health.assert_called_once()


class TestLokiClient:
    """Loki客户端测试"""

    @pytest.fixture
    def loki_client(self):
        """创建Loki客户端实例"""
        return LokiClient(base_url="http://localhost:3100")

    @pytest.mark.asyncio
    async def test_query_instant(self, loki_client):
        """测试即时查询"""
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "varlogs"},
                        "values": [[1234567890000000000, "test log message"]],
                    }
                ],
            },
        }

        with patch.object(loki_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await loki_client.query(query='{job="varlogs"}')

            assert result.status == "success"
            assert result.data["resultType"] == "streams"
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_logs(self, loki_client):
        """测试搜索日志"""
        mock_response = {
            "status": "success",
            "data": {
                "resultType": "streams",
                "result": [
                    {
                        "stream": {"job": "varlogs", "level": "error"},
                        "values": [[1234567890000000000, "ERROR: test error"]],
                    }
                ],
            },
        }

        with patch.object(loki_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            logs = await loki_client.search_logs(query='level="error"', time_range="1h")

            assert len(logs) > 0
            assert logs[0]["level"] == "error"

    @pytest.mark.asyncio
    async def test_get_error_logs(self, loki_client):
        """测试获取错误日志"""
        with patch.object(loki_client, "search_logs", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {"timestamp": "2024-01-01T00:00:00Z", "message": "ERROR: test", "labels": {}}
            ]

            logs = await loki_client.get_error_logs(time_range="1h")

            assert len(logs) > 0
            mock_search.assert_called_once()


class TestTempoClient:
    """Tempo客户端测试"""

    @pytest.fixture
    def tempo_client(self):
        """创建Tempo客户端实例"""
        return TempoClient(base_url="http://localhost:3200")

    @pytest.mark.asyncio
    async def test_search_traces(self, tempo_client):
        """测试搜索追踪"""
        mock_response = {
            "traces": [
                {
                    "traceID": "trace-001",
                    "rootTraceName": "api-service",
                    "rootServiceName": "api",
                    "startTimeUnixNano": "1234567890000000000",
                    "durationMs": 150,
                }
            ],
            "totalTraces": 1,
            "limit": 20,
            "offset": 0,
        }

        with patch.object(tempo_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            start = datetime.now(timezone.utc) - timedelta(hours=1)
            end = datetime.now(timezone.utc)

            result = await tempo_client.search_traces(
                query="{}", start=start, end=end, limit=20
            )

            assert result.totalTraces == 1
            assert len(result.traces) == 1
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_trace(self, tempo_client):
        """测试获取追踪"""
        mock_response = {
            "data": {
                "traceID": "trace-001",
                "spans": [
                    {
                        "traceID": "trace-001",
                        "spanID": "span-001",
                        "operationName": "GET /api",
                        "startTime": "2024-01-01T00:00:00Z",
                        "duration": 150000000,
                    }
                ],
            }
        }

        with patch.object(tempo_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await tempo_client.get_trace(trace_id="trace-001")

            assert result.traceID == "trace-001"
            assert len(result.spans) == 1
            mock_request.assert_called_once()


class TestElasticsearchClient:
    """Elasticsearch客户端测试"""

    @pytest.fixture
    def elasticsearch_client(self):
        """创建Elasticsearch客户端实例"""
        return ElasticsearchClient(base_url="http://localhost:9200")

    @pytest.mark.asyncio
    async def test_search(self, elasticsearch_client):
        """测试搜索"""
        mock_response = {
            "took": 5,
            "timed_out": False,
            "_shards": {"total": 5, "successful": 5, "failed": 0},
            "hits": {
                "total": {"value": 1, "relation": "eq"},
                "hits": [
                    {
                        "_index": "logs-2024.01.01",
                        "_id": "doc-001",
                        "_score": 1.0,
                        "_source": {
                            "timestamp": "2024-01-01T00:00:00Z",
                            "message": "test log",
                            "level": "info",
                        },
                    }
                ],
            },
        }

        with patch.object(elasticsearch_client, "_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response

            result = await elasticsearch_client.search(
                index="logs-*", query={"query_string": {"query": "test"}}
            )

            assert result.took == 5
            assert result.hits["total"]["value"] == 1
            mock_request.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_logs(self, elasticsearch_client):
        """测试搜索日志"""
        with patch.object(elasticsearch_client, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = MagicMock(
                hits={"hits": [{"_source": {"timestamp": "2024-01-01T00:00:00Z", "message": "test"}}]}
            )

            logs = await elasticsearch_client.search_logs(
                index="logs-*", query_string="test", time_range="1h"
            )

            assert len(logs) > 0
            mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, elasticsearch_client):
        """测试健康检查"""
        with patch.object(elasticsearch_client, "get_cluster_health", new_callable=AsyncMock) as mock_health:
            mock_health.return_value = {"status": "green"}

            result = await elasticsearch_client.health_check()

            assert result is True
            mock_health.assert_called_once()
