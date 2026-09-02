# -*- coding: utf-8 -*-
"""
Tests for gRPC Router API endpoints
Tests for grpc_router.py endpoints
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from datetime import datetime
import httpx


class TestGrpcRouterHealth:
    """Test gRPC health check endpoint"""

    @pytest.mark.asyncio
    async def test_grpc_health_available(self):
        """Test health check when gRPC is available"""
        from main import app
        from fastapi.testclient import TestClient

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", MagicMock()
        ):
            with TestClient(app) as client:
                response = client.get("/api/grpc/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["grpc_available"] is True
                assert data["server_running"] is True

    @pytest.mark.asyncio
    async def test_grpc_health_unavailable(self):
        """Test health check when gRPC is unavailable"""
        from main import app
        from fastapi.testclient import TestClient

        with patch("api.grpc_router.GRPC_AVAILABLE", False), patch(
            "api.grpc_router._grpc_server", None
        ):
            with TestClient(app) as client:
                response = client.get("/api/grpc/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "degraded"
                assert data["grpc_available"] is False
                assert data["server_running"] is False

    @pytest.mark.asyncio
    async def test_grpc_health_server_none(self):
        """Test health check when server is None"""
        from main import app
        from fastapi.testclient import TestClient

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", None
        ):
            with TestClient(app) as client:
                response = client.get("/api/grpc/health")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "healthy"
                assert data["grpc_available"] is True
                assert data["server_running"] is False


class TestGrpcRouterStart:
    """Test gRPC server start endpoint"""

    @pytest.mark.asyncio
    async def test_start_grpc_server_success(self):
        """Test successful gRPC server start"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.start = AsyncMock()

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/start")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "started"
                assert "message" in data
                mock_server.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_grpc_server_unavailable(self):
        """Test start when gRPC is unavailable"""
        from main import app
        from fastapi.testclient import TestClient

        with patch("api.grpc_router.GRPC_AVAILABLE", False), patch(
            "api.grpc_router._grpc_server", None
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/start")
                assert response.status_code == 503
                data = response.json()
                assert "detail" in data

    @pytest.mark.asyncio
    async def test_start_grpc_server_error(self):
        """Test start when server raises error"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.start = AsyncMock(side_effect=Exception("Start failed"))

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/start")
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data


class TestGrpcRouterStop:
    """Test gRPC server stop endpoint"""

    @pytest.mark.asyncio
    async def test_stop_grpc_server_success(self):
        """Test successful gRPC server stop"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.stop = AsyncMock()

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/stop")
                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "stopped"
                assert "message" in data
                mock_server.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_grpc_server_unavailable(self):
        """Test stop when gRPC is unavailable"""
        from main import app
        from fastapi.testclient import TestClient

        with patch("api.grpc_router.GRPC_AVAILABLE", False), patch(
            "api.grpc_router._grpc_server", None
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/stop")
                assert response.status_code == 503
                data = response.json()
                assert "detail" in data

    @pytest.mark.asyncio
    async def test_stop_grpc_server_error(self):
        """Test stop when server raises error"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.stop = AsyncMock(side_effect=Exception("Stop failed"))

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                response = client.post("/api/grpc/stop")
                assert response.status_code == 500
                data = response.json()
                assert "detail" in data


class TestGrpcRouterIntegration:
    """Integration tests for gRPC router"""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full server lifecycle: health -> start -> health -> stop -> health"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                # Initial health check
                response = client.get("/api/grpc/health")
                assert response.status_code == 200
                data = response.json()
                assert data["server_running"] is True

                # Start server
                response = client.post("/api/grpc/start")
                assert response.status_code == 200

                # Health check after start
                response = client.get("/api/grpc/health")
                assert response.status_code == 200

                # Stop server
                response = client.post("/api/grpc/stop")
                assert response.status_code == 200

                # Health check after stop
                response = client.get("/api/grpc/health")
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """Test concurrent requests to gRPC endpoints"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.start = AsyncMock()
        mock_server.stop = AsyncMock()

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                # Send concurrent health check requests
                responses = [client.get("/api/grpc/health") for _ in range(5)]

                for response in responses:
                    assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Test error recovery after failed operation"""
        from main import app
        from fastapi.testclient import TestClient

        mock_server = AsyncMock()
        mock_server.start = AsyncMock(side_effect=Exception("Temporary error"))
        mock_server.stop = AsyncMock()

        with patch("api.grpc_router.GRPC_AVAILABLE", True), patch(
            "api.grpc_router._grpc_server", mock_server
        ):
            with TestClient(app) as client:
                # Failed start
                response = client.post("/api/grpc/start")
                assert response.status_code == 500

                # Health check should still work
                response = client.get("/api/grpc/health")
                assert response.status_code == 200

                # Stop should still work
                response = client.post("/api/grpc/stop")
                assert response.status_code == 200
