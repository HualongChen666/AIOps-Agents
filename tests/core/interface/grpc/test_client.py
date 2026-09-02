# -*- coding: utf-8 -*-
"""
Tests for gRPC Client
Tests for core.interface.grpc.client.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.interface.grpc.client import AIOpsGrpcClient


class TestAIOpsGrpcClientInit:
    """Test AIOpsGrpcClient initialization"""

    def test_client_initialization_default(self):
        """Test client initialization with default parameters"""
        client = AIOpsGrpcClient()
        assert client.host == "localhost"
        assert client.port == 50051
        assert client.timeout == 30.0
        assert client._channel is None
        assert client._grpc_client is None

    def test_client_initialization_custom(self):
        """Test client initialization with custom parameters"""
        client = AIOpsGrpcClient(host="192.168.1.1", port=8080, timeout=60.0)
        assert client.host == "192.168.1.1"
        assert client.port == 8080
        assert client.timeout == 60.0
        assert client._channel is None
        assert client._grpc_client is None

    def test_client_initialization_different_host(self):
        """Test client initialization with different host"""
        client = AIOpsGrpcClient(host="grpc.example.com")
        assert client.host == "grpc.example.com"
        assert client.port == 50051

    def test_client_initialization_different_port(self):
        """Test client initialization with different port"""
        client = AIOpsGrpcClient(port=9000)
        assert client.host == "localhost"
        assert client.port == 9000

    def test_client_initialization_different_timeout(self):
        """Test client initialization with different timeout"""
        client = AIOpsGrpcClient(timeout=120.0)
        assert client.timeout == 120.0

    def test_client_initialization_zero_timeout(self):
        """Test client initialization with zero timeout"""
        client = AIOpsGrpcClient(timeout=0.0)
        assert client.timeout == 0.0

    def test_client_initialization_large_timeout(self):
        """Test client initialization with large timeout"""
        client = AIOpsGrpcClient(timeout=3600.0)
        assert client.timeout == 3600.0


class TestAIOpsGrpcClientConnect:
    """Test client connect functionality"""

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful client connection"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            assert client._channel is not None
            mock_grpc.aio.insecure_channel.assert_called_once_with("localhost:50051")
            mock_channel.ready.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_custom_host_port(self):
        """Test connection with custom host and port"""
        client = AIOpsGrpcClient(host="192.168.1.1", port=8080)

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            mock_grpc.aio.insecure_channel.assert_called_once_with("192.168.1.1:8080")

    @pytest.mark.asyncio
    async def test_connect_error(self):
        """Test connection with error"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_grpc.aio.insecure_channel = MagicMock(side_effect=Exception("Connection error"))

            with pytest.raises(Exception, match="Connection error"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_timeout_error(self):
        """Test connection with timeout error"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock(side_effect=Exception("Timeout"))
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            with pytest.raises(Exception, match="Timeout"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_connect_twice(self):
        """Test connecting twice"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()
            await client.connect()

            assert mock_grpc.aio.insecure_channel.call_count == 2

    @pytest.mark.asyncio
    async def test_connect_ipv6(self):
        """Test connection with IPv6 address"""
        client = AIOpsGrpcClient(host="::1", port=50051)

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            mock_grpc.aio.insecure_channel.assert_called_once_with("::1:50051")


class TestAIOpsGrpcClientClose:
    """Test client close functionality"""

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test successful client close"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()
            await client.close()

            mock_channel.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_connect(self):
        """Test closing without connecting"""
        client = AIOpsGrpcClient()

        # Should not raise error even if never connected
        await client.close()

    @pytest.mark.asyncio
    async def test_close_error(self):
        """Test close with error"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock(side_effect=Exception("Close error"))
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            with pytest.raises(Exception, match="Close error"):
                await client.close()

    @pytest.mark.asyncio
    async def test_close_multiple_times(self):
        """Test closing multiple times"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()
            await client.close()
            await client.close()

            # Should be called twice since we call close twice
            assert mock_channel.close.call_count == 2


class TestAIOpsGrpcClientGetMetrics:
    """Test get metrics functionality"""

    @pytest.mark.asyncio
    async def test_get_metrics_not_implemented(self):
        """Test that get_metrics raises RuntimeError when not connected"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_metrics()

    @pytest.mark.asyncio
    async def test_get_metrics_after_connect(self):
        """Test get_metrics after connect still raises RuntimeError"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            with pytest.raises(RuntimeError, match="gRPC client not initialized"):
                await client.get_metrics()


class TestAIOpsGrpcClientGetAlerts:
    """Test get alerts functionality"""

    @pytest.mark.asyncio
    async def test_get_alerts_not_implemented(self):
        """Test that get_alerts raises RuntimeError when not connected"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_alerts()

    @pytest.mark.asyncio
    async def test_get_alerts_with_filters(self):
        """Test get_alerts with filters still raises RuntimeError"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_alerts(level="critical", platform="prometheus", limit=5)

    @pytest.mark.asyncio
    async def test_get_alerts_with_default_limit(self):
        """Test get_alerts with default limit still raises RuntimeError"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_alerts(limit=10)


class TestAIOpsGrpcClientExecuteRepair:
    """Test execute repair functionality"""

    @pytest.mark.asyncio
    async def test_execute_repair_not_implemented(self):
        """Test that execute_repair raises RuntimeError when not connected"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.execute_repair("restart_service")

    @pytest.mark.asyncio
    async def test_execute_repair_with_parameters(self):
        """Test execute_repair with parameters still raises RuntimeError"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.execute_repair("restart_service", {"service": "nginx"})

    @pytest.mark.asyncio
    async def test_execute_repair_with_none_parameters(self):
        """Test execute_repair with None parameters still raises RuntimeError"""
        client = AIOpsGrpcClient()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.execute_repair("restart_service", None)


class TestAIOpsGrpcClientStreamMetrics:
    """Test stream metrics functionality"""

    @pytest.mark.asyncio
    async def test_stream_metrics_not_implemented(self):
        """Test that stream_metrics raises NotImplementedError"""
        client = AIOpsGrpcClient()

        with pytest.raises(NotImplementedError, match="gRPC metrics streaming requires"):
            async for _ in client.stream_metrics():
                pass

    @pytest.mark.asyncio
    async def test_stream_metrics_is_generator(self):
        """Test that stream_metrics is an async generator"""
        client = AIOpsGrpcClient()

        with pytest.raises(NotImplementedError):
            result = client.stream_metrics()
            # Verify it's an async generator
            assert hasattr(result, "__aiter__")
            async for _ in result:
                pass


class TestAIOpsGrpcClientLifecycle:
    """Test full client lifecycle"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete client lifecycle: connect -> close"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            # Connect
            await client.connect()
            assert client._channel is not None

            # Close
            await client.close()

            mock_channel.ready.assert_called_once()
            mock_channel.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect(self):
        """Test reconnecting after close"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            # First connection
            await client.connect()
            await client.close()

            # Second connection
            await client.connect()
            await client.close()

            assert mock_grpc.aio.insecure_channel.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_connect_close_cycles(self):
        """Test multiple connect/close cycles"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            for _ in range(3):
                await client.connect()
                await client.close()

            assert mock_grpc.aio.insecure_channel.call_count == 3
            assert mock_channel.close.call_count == 3


class TestAIOpsGrpcClientConfiguration:
    """Test client configuration scenarios"""

    @pytest.mark.asyncio
    async def test_client_with_different_hosts(self):
        """Test client with different host configurations"""
        hosts = ["localhost", "127.0.0.1", "0.0.0.0", "192.168.1.1", "grpc.example.com"]

        for host in hosts:
            client = AIOpsGrpcClient(host=host)

            with patch("core.interface.grpc.client.grpc") as mock_grpc:
                mock_channel = AsyncMock()
                mock_channel.ready = AsyncMock()
                mock_channel.close = AsyncMock()
                mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

                await client.connect()
                await client.close()

                mock_grpc.aio.insecure_channel.assert_called_once_with(f"{host}:50051")

    @pytest.mark.asyncio
    async def test_client_with_different_ports(self):
        """Test client with different port configurations"""
        ports = [50051, 8080, 9000, 10000, 65535]

        for port in ports:
            client = AIOpsGrpcClient(port=port)

            with patch("core.interface.grpc.client.grpc") as mock_grpc:
                mock_channel = AsyncMock()
                mock_channel.ready = AsyncMock()
                mock_channel.close = AsyncMock()
                mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

                await client.connect()
                await client.close()

                mock_grpc.aio.insecure_channel.assert_called_once_with(f"localhost:{port}")

    @pytest.mark.asyncio
    async def test_client_with_different_timeouts(self):
        """Test client with different timeout configurations"""
        timeouts = [5.0, 10.0, 30.0, 60.0, 120.0]

        for timeout in timeouts:
            client = AIOpsGrpcClient(timeout=timeout)
            assert client.timeout == timeout


class TestAIOpsGrpcClientErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_grpc_import_error(self):
        """Test handling of grpc import error"""
        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc.aio.insecure_channel", side_effect=Exception("No grpc")):
            with pytest.raises(Exception, match="No grpc"):
                await client.connect()

    @pytest.mark.asyncio
    async def test_concurrent_connect_attempts(self):
        """Test concurrent connect attempts"""
        import asyncio

        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            # Attempt concurrent connects
            await asyncio.gather(client.connect(), client.connect(), client.connect())

            # Should have been called 3 times
            assert mock_grpc.aio.insecure_channel.call_count == 3

    @pytest.mark.asyncio
    async def test_concurrent_close_attempts(self):
        """Test concurrent close attempts"""
        import asyncio

        client = AIOpsGrpcClient()

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_channel.close = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            # Attempt concurrent closes
            await asyncio.gather(client.close(), client.close(), client.close())

            # Should be called 3 times since we call close 3 times
            assert mock_channel.close.call_count == 3

    @pytest.mark.asyncio
    async def test_call_methods_without_connect(self):
        """Test calling methods without connecting"""
        client = AIOpsGrpcClient()

        # All methods should raise appropriate errors
        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_metrics()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.get_alerts()

        with pytest.raises(RuntimeError, match="gRPC client not initialized"):
            await client.execute_repair("test")

        with pytest.raises(NotImplementedError, match="gRPC metrics streaming requires"):
            async for _ in client.stream_metrics():
                pass


class TestAIOpsGrpcClientEdgeCases:
    """Test edge cases and boundary conditions"""

    @pytest.mark.asyncio
    async def test_connect_with_very_long_host(self):
        """Test connection with very long hostname"""
        long_host = "a" * 1000 + ".example.com"
        client = AIOpsGrpcClient(host=long_host)

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            mock_grpc.aio.insecure_channel.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_with_special_characters(self):
        """Test connection with special characters in host"""
        special_host = "test-host_example.com"
        client = AIOpsGrpcClient(host=special_host)

        with patch("core.interface.grpc.client.grpc") as mock_grpc:
            mock_channel = AsyncMock()
            mock_channel.ready = AsyncMock()
            mock_grpc.aio.insecure_channel = MagicMock(return_value=mock_channel)

            await client.connect()

            mock_grpc.aio.insecure_channel.assert_called_once_with(f"{special_host}:50051")

    @pytest.mark.asyncio
    async def test_negative_timeout(self):
        """Test client with negative timeout (should accept but may cause issues)"""
        client = AIOpsGrpcClient(timeout=-10.0)
        assert client.timeout == -10.0

    @pytest.mark.asyncio
    async def test_very_large_timeout(self):
        """Test client with very large timeout"""
        client = AIOpsGrpcClient(timeout=999999.0)
        assert client.timeout == 999999.0
