# -*- coding: utf-8 -*-
"""
gRPC Tests
"""

import pytest

from core.interface.grpc import (
    AIOpsGrpcClient,
    AIOpsGrpcServer,
    AuthInterceptor,
    LoggingInterceptor,
    MetricsInterceptor,
)


class TestAIOpsGrpcServer:
    """Test gRPC server"""

    def test_init(self):
        """Test server initialization"""
        server = AIOpsGrpcServer()
        assert server.host == "127.0.0.1"
        assert server.port == 50051
        assert server.max_workers == 10


class TestAIOpsGrpcClient:
    """Test gRPC client"""

    def test_init(self):
        """Test client initialization"""
        client = AIOpsGrpcClient()
        assert client.host == "localhost"
        assert client.port == 50051

    @pytest.mark.asyncio
    async def test_get_metrics(self):
        """Test getting metrics"""
        client = AIOpsGrpcClient()
        metrics = await client.get_metrics()
        assert "cpu_usage" in metrics
        assert "memory_usage" in metrics

    @pytest.mark.asyncio
    async def test_get_alerts(self):
        """Test getting alerts"""
        client = AIOpsGrpcClient()
        alerts = await client.get_alerts()
        assert isinstance(alerts, list)

    @pytest.mark.asyncio
    async def test_execute_repair(self):
        """Test executing repair"""
        client = AIOpsGrpcClient()
        result = await client.execute_repair("test_script")
        assert "script_key" in result


class TestInterceptors:
    """Test gRPC interceptors"""

    def test_logging_interceptor(self):
        """Test logging interceptor"""
        interceptor = LoggingInterceptor()
        assert interceptor is not None

    def test_auth_interceptor(self):
        """Test auth interceptor"""
        interceptor = AuthInterceptor("test-api-key")
        assert interceptor.api_key == "test-api-key"

    def test_metrics_interceptor(self):
        """Test metrics interceptor"""
        interceptor = MetricsInterceptor()
        assert interceptor.get_metrics() == {}
