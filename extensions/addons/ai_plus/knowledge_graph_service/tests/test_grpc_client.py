# -*- coding: utf-8 -*-
"""Tests for KnowledgeGraphRPCClient module."""

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from extensions.addons.ai_plus.knowledge_graph_service.grpc.client import (
    KnowledgeGraphRPCClient,
)


class TestKnowledgeGraphRPCClient:
    """Test cases for KnowledgeGraphRPCClient class."""

    def test_initialization_default(self):
        """Test initialization with default URL."""
        client = KnowledgeGraphRPCClient()
        assert client.base_url == "http://localhost:9409"

    def test_initialization_custom_url(self):
        """Test initialization with custom URL."""
        client = KnowledgeGraphRPCClient(base_url="http://custom:8080")
        assert client.base_url == "http://custom:8080"

    def test_initialization_with_https(self):
        """Test initialization with HTTPS URL."""
        client = KnowledgeGraphRPCClient(base_url="https://secure:9409")
        assert client.base_url == "https://secure:9409"

    def test_initialization_with_path(self):
        """Test initialization with URL containing path."""
        client = KnowledgeGraphRPCClient(base_url="http://localhost:9409/api")
        assert client.base_url == "http://localhost:9409/api"

    def test_initialization_with_port(self):
        """Test initialization with custom port."""
        client = KnowledgeGraphRPCClient(base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"

    def test_initialization_stores_url(self):
        """Test that URL is stored correctly."""
        client = KnowledgeGraphRPCClient(base_url="http://example.com:9000/rpc")
        assert client.base_url == "http://example.com:9000/rpc"

    @pytest.mark.asyncio
    async def test_call_success(self):
        """Test successful RPC call (covers lines 19-22)."""
        client = KnowledgeGraphRPCClient(base_url="http://localhost:9409")

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.call("test_method", {"key": "value"})
            assert result == {"result": "success"}
            mock_client.post.assert_called_once_with(
                "http://localhost:9409/rpc/test_method", json={"key": "value"}
            )

    @pytest.mark.asyncio
    async def test_call_with_none_payload(self):
        """Test RPC call with None payload (covers lines 19-22)."""
        client = KnowledgeGraphRPCClient(base_url="http://localhost:9409")

        # Mock httpx.AsyncClient
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await client.call("test_method", None)
            assert result == {"result": "ok"}
            mock_client.post.assert_called_once_with(
                "http://localhost:9409/rpc/test_method", json={}
            )

    @pytest.mark.asyncio
    async def test_call_http_error(self):
        """Test RPC call with HTTP error (covers lines 19-22)."""
        client = KnowledgeGraphRPCClient(base_url="http://localhost:9409")

        # Mock httpx.AsyncClient to raise HTTP error
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(side_effect=httpx.HTTPStatusError(
            "404 Not Found", request=MagicMock(), response=MagicMock()
        ))

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await client.call("nonexistent_method", {})
