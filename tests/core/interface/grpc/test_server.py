# -*- coding: utf-8 -*-
"""
Tests for gRPC Server
Tests for core.interface.grpc.server.py
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from core.interface.grpc.server import AIOpsGrpcServer


class TestAIOpsGrpcServerInit:
    """Test AIOpsGrpcServer initialization"""

    def test_server_initialization_default(self):
        """Test server initialization with default parameters"""
        server = AIOpsGrpcServer()
        assert server.host == "127.0.0.1"
        assert server.port == 50051
        assert server.max_workers == 10
        assert server._server is None

    def test_server_initialization_custom(self):
        """Test server initialization with custom parameters"""
        server = AIOpsGrpcServer(host="0.0.0.0", port=8080, max_workers=20)
        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.max_workers == 20
        assert server._server is None

    def test_server_initialization_different_host(self):
        """Test server initialization with different host"""
        server = AIOpsGrpcServer(host="localhost")
        assert server.host == "localhost"
        assert server.port == 50051

    def test_server_initialization_different_port(self):
        """Test server initialization with different port"""
        server = AIOpsGrpcServer(port=9000)
        assert server.host == "127.0.0.1"
        assert server.port == 9000

    def test_server_initialization_different_workers(self):
        """Test server initialization with different worker count"""
        server = AIOpsGrpcServer(max_workers=5)
        assert server.max_workers == 5


class TestAIOpsGrpcServerStart:
    """Test server start functionality"""

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful server start"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            assert server._server is not None
            mock_server.add_insecure_port.assert_called_once_with("127.0.0.1:50051")
            mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_custom_host_port(self):
        """Test server start with custom host and port"""
        server = AIOpsGrpcServer(host="0.0.0.0", port=8080)

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_server.add_insecure_port.assert_called_once_with("0.0.0.0:8080")

    @pytest.mark.asyncio
    async def test_start_error(self):
        """Test server start with error"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_grpc.server = MagicMock(side_effect=Exception("Start error"))

            with pytest.raises(Exception, match="Start error"):
                await server.start()

    @pytest.mark.asyncio
    async def test_start_twice(self):
        """Test starting server twice"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()
            await server.start()

            assert mock_server.start.call_count == 2

    @pytest.mark.asyncio
    async def test_start_with_threadpool_executor(self):
        """Test that ThreadPoolExecutor is created with correct max_workers"""
        server = AIOpsGrpcServer(max_workers=15)

        with patch("core.interface.grpc.server.grpc") as mock_grpc, patch(
            "core.interface.grpc.server.futures"
        ) as mock_futures:
            mock_executor = MagicMock()
            mock_futures.ThreadPoolExecutor = MagicMock(return_value=mock_executor)
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_futures.ThreadPoolExecutor.assert_called_once_with(max_workers=15)


class TestAIOpsGrpcServerStop:
    """Test server stop functionality"""

    @pytest.mark.asyncio
    async def test_stop_success(self):
        """Test successful server stop"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.stop = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()
            await server.stop()

            mock_server.stop.assert_called_once_with(grace=5)

    @pytest.mark.asyncio
    async def test_stop_without_start(self):
        """Test stopping server without starting it"""
        server = AIOpsGrpcServer()

        # Should not raise error even if server was never started
        await server.stop()

    @pytest.mark.asyncio
    async def test_stop_error(self):
        """Test server stop with error"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.stop = MagicMock(side_effect=Exception("Stop error"))
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            with pytest.raises(Exception, match="Stop error"):
                await server.stop()

    @pytest.mark.asyncio
    async def test_stop_custom_grace(self):
        """Test that stop uses default grace period"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.stop = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()
            await server.stop()

            # Verify grace parameter is 5 (default)
            mock_server.stop.assert_called_once()
            call_args = mock_server.stop.call_args
            assert call_args[1]["grace"] == 5


class TestAIOpsGrpcServerWaitForTermination:
    """Test server wait for termination"""

    @pytest.mark.asyncio
    async def test_wait_for_termination_success(self):
        """Test successful wait for termination"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.wait_for_termination = AsyncMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()
            await server.wait_for_termination()

            mock_server.wait_for_termination.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_for_termination_without_start(self):
        """Test wait for termination without starting server"""
        server = AIOpsGrpcServer()

        # Should not raise error even if server was never started
        await server.wait_for_termination()

    @pytest.mark.asyncio
    async def test_wait_for_termination_error(self):
        """Test wait for termination with error"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.wait_for_termination = AsyncMock(
                side_effect=Exception("Termination error")
            )
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            with pytest.raises(Exception, match="Termination error"):
                await server.wait_for_termination()


class TestAIOpsGrpcServerLifecycle:
    """Test full server lifecycle"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test complete server lifecycle: start -> wait -> stop"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_server.stop = MagicMock()
            mock_server.wait_for_termination = AsyncMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            # Start
            await server.start()
            assert server._server is not None

            # Wait for termination
            await server.wait_for_termination()

            # Stop
            await server.stop()

            mock_server.start.assert_called_once()
            mock_server.wait_for_termination.assert_called_once()
            mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_restart_server(self):
        """Test restarting server"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_server.stop = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            # First start
            await server.start()
            await server.stop()

            # Second start
            await server.start()
            await server.stop()

            assert mock_server.start.call_count == 2
            assert mock_server.stop.call_count == 2

    @pytest.mark.asyncio
    async def test_multiple_start_stop_cycles(self):
        """Test multiple start/stop cycles"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_server.stop = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            for _ in range(3):
                await server.start()
                await server.stop()

            assert mock_server.start.call_count == 3
            assert mock_server.stop.call_count == 3


class TestAIOpsGrpcServerConfiguration:
    """Test server configuration scenarios"""

    @pytest.mark.asyncio
    async def test_server_with_ipv6(self):
        """Test server with IPv6 address"""
        server = AIOpsGrpcServer(host="::1", port=50051)

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_server.add_insecure_port.assert_called_once_with("::1:50051")

    @pytest.mark.asyncio
    async def test_server_with_high_port(self):
        """Test server with high port number"""
        server = AIOpsGrpcServer(port=65535)

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_server.add_insecure_port.assert_called_once_with("127.0.0.1:65535")

    @pytest.mark.asyncio
    async def test_server_with_single_worker(self):
        """Test server with single worker"""
        server = AIOpsGrpcServer(max_workers=1)

        with patch("core.interface.grpc.server.grpc") as mock_grpc, patch(
            "core.interface.grpc.server.futures"
        ) as mock_futures:
            mock_executor = MagicMock()
            mock_futures.ThreadPoolExecutor = MagicMock(return_value=mock_executor)
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_futures.ThreadPoolExecutor.assert_called_once_with(max_workers=1)

    @pytest.mark.asyncio
    async def test_server_with_many_workers(self):
        """Test server with many workers"""
        server = AIOpsGrpcServer(max_workers=100)

        with patch("core.interface.grpc.server.grpc") as mock_grpc, patch(
            "core.interface.grpc.server.futures"
        ) as mock_futures:
            mock_executor = MagicMock()
            mock_futures.ThreadPoolExecutor = MagicMock(return_value=mock_executor)
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            mock_futures.ThreadPoolExecutor.assert_called_once_with(max_workers=100)


class TestAIOpsGrpcServerErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_grpc_import_error(self):
        """Test handling of grpc import error"""
        # This test verifies the error handling if grpc module is not available
        # In the actual implementation, this would be caught at import time
        # Since grpc is already imported, we test that the error propagates correctly
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc.server", side_effect=Exception("No grpc")):
            with pytest.raises(Exception, match="No grpc"):
                await server.start()

    @pytest.mark.asyncio
    async def test_concurrent_start_attempts(self):
        """Test concurrent start attempts"""
        import asyncio

        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_grpc.server = MagicMock(return_value=mock_server)

            # Attempt concurrent starts
            await asyncio.gather(server.start(), server.start(), server.start())

            # Should have been called 3 times
            assert mock_server.start.call_count == 3

    @pytest.mark.asyncio
    async def test_stop_during_wait(self):
        """Test stopping while waiting for termination"""
        server = AIOpsGrpcServer()

        with patch("core.interface.grpc.server.grpc") as mock_grpc:
            mock_server = MagicMock()
            mock_server.add_insecure_port = MagicMock()
            mock_server.start = MagicMock()
            mock_server.stop = MagicMock()
            mock_server.wait_for_termination = AsyncMock(side_effect=Exception("Interrupted"))
            mock_grpc.server = MagicMock(return_value=mock_server)

            await server.start()

            with pytest.raises(Exception, match="Interrupted"):
                await server.wait_for_termination()

            # Should still be able to stop
            await server.stop()
            mock_server.stop.assert_called_once()
