# -*- coding: utf-8 -*-
"""
Unit tests for L4 Storage Layer
Tests for VictoriaMetrics, Loki, Tempo adapters and retry mechanisms
"""

import asyncio
from datetime import datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.storage.l4.loki import LokiStorage
from core.storage.l4.retry import (
    BufferedWriter,
    ConnectionPoolConfig,
    FallbackStorage,
    RetryConfig,
    with_retry,
)
from core.storage.l4.tempo import TempoStorage
from core.storage.l4.victoriametrics import VictoriaMetricsStorage


class TestRetryConfig:
    """Test retry configuration"""

    def test_default_config(self):
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 30.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_custom_config(self):
        config = RetryConfig(max_retries=5, base_delay=0.5)
        assert config.max_retries == 5
        assert config.base_delay == 0.5


class TestWithRetry:
    """Test retry decorator"""

    @pytest.mark.asyncio
    async def test_successful_call(self):
        """Test that successful call doesn't retry"""
        mock_func = AsyncMock(return_value="success")
        decorated = with_retry()(mock_func)

        result = await decorated()
        assert result == "success"
        mock_func.assert_called_once()

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Test that failed call retries and eventually succeeds"""
        mock_func = AsyncMock(side_effect=[Exception("fail"), "success"])
        config = RetryConfig(max_retries=3, base_delay=0.01)
        decorated = with_retry(config)(mock_func)

        result = await decorated()
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries are respected"""
        mock_func = AsyncMock(side_effect=Exception("fail"))
        config = RetryConfig(max_retries=2, base_delay=0.01)
        decorated = with_retry(config)(mock_func)

        with pytest.raises(Exception):
            await decorated()
        assert mock_func.call_count == 3  # initial + 2 retries


class TestFallbackStorage:
    """Test fallback storage mechanism"""

    @pytest.mark.asyncio
    async def test_primary_success(self):
        """Test successful primary storage usage"""
        primary = AsyncMock()
        primary.store = AsyncMock(return_value=True)
        fallback = AsyncMock()

        fb_storage = FallbackStorage(primary, fallback, fallback_enabled=True)
        result = await fb_storage.store("key", "value")

        assert result is True
        primary.store.assert_called_once()
        fallback.store.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_on_primary_failure(self):
        """Test fallback when primary fails"""
        primary = AsyncMock()
        primary.store = AsyncMock(side_effect=Exception("primary failed"))
        fallback = AsyncMock()
        fallback.store = AsyncMock(return_value=True)

        fb_storage = FallbackStorage(primary, fallback, fallback_enabled=True)
        result = await fb_storage.store("key", "value")

        assert result is True
        fallback.store.assert_called_once()

    @pytest.mark.asyncio
    async def test_both_fail(self):
        """Test when both primary and fallback fail"""
        primary = AsyncMock()
        primary.store = AsyncMock(side_effect=Exception("primary failed"))
        fallback = AsyncMock()
        fallback.store = AsyncMock(side_effect=Exception("fallback failed"))

        fb_storage = FallbackStorage(primary, fallback, fallback_enabled=True)
        result = await fb_storage.store("key", "value")

        assert result is False

    @pytest.mark.asyncio
    async def test_primary_recovery(self):
        """Test switching back to primary after recovery"""
        primary = AsyncMock()
        primary.store = AsyncMock(side_effect=[Exception("fail"), True])
        primary.get_status = MagicMock(return_value={"initialized": True, "connected": True})
        fallback = AsyncMock()
        fallback.store = AsyncMock(return_value=True)

        fb_storage = FallbackStorage(primary, fallback, fallback_enabled=True)

        # First call fails, switches to fallback
        result1 = await fb_storage.store("key", "value")
        assert result1 is True
        assert fb_storage._use_fallback is True

        # Check primary availability
        await fb_storage.check_primary_availability()

        # Second call should use primary
        result2 = await fb_storage.store("key", "value")
        assert result2 is True


class TestBufferedWriter:
    """Test buffered writer"""

    @pytest.mark.asyncio
    async def test_buffer_flush_on_size(self):
        """Test flush when buffer reaches size"""
        storage = AsyncMock()
        storage.store = AsyncMock(return_value=True)

        writer = BufferedWriter(storage, buffer_size=3, flush_interval=60)
        await writer.start()

        await writer.write("key1", "value1")
        await writer.write("key2", "value2")
        await writer.write("key3", "value3")  # Should trigger flush

        await asyncio.sleep(0.1)  # Allow flush to complete
        assert storage.store.call_count == 3
        await writer.stop()

    @pytest.mark.asyncio
    async def test_periodic_flush(self):
        """Test periodic flush on interval"""
        storage = AsyncMock()
        storage.store = AsyncMock(return_value=True)

        writer = BufferedWriter(storage, buffer_size=100, flush_interval=0.1)
        await writer.start()

        await writer.write("key1", "value1")
        await asyncio.sleep(0.2)  # Wait for periodic flush
        assert storage.store.call_count == 1
        await writer.stop()

    @pytest.mark.asyncio
    async def test_flush_on_stop(self):
        """Test flush on stop"""
        storage = AsyncMock()
        storage.store = AsyncMock(return_value=True)

        writer = BufferedWriter(storage, buffer_size=100, flush_interval=60)
        await writer.start()

        await writer.write("key1", "value1")
        await writer.stop()

        assert storage.store.call_count == 1


class TestConnectionPoolConfig:
    """Test connection pool configuration"""

    def test_default_config(self):
        config = ConnectionPoolConfig()
        assert config.max_connections == 100
        assert config.max_keepalive_connections == 20
        assert config.keepalive_expiry == 5.0
        assert config.timeout == 30.0

    def test_custom_config(self):
        config = ConnectionPoolConfig(max_connections=200, timeout=60.0)
        assert config.max_connections == 200
        assert config.timeout == 60.0


class TestVictoriaMetricsStorage:
    """Test VictoriaMetrics storage adapter"""

    @pytest.mark.asyncio
    async def test_store_metric(self):
        """Test storing a metric"""
        config = {"base_url": "http://localhost:8428"}
        storage = VictoriaMetricsStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 204
            mock_client.post = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.store("test_metric", 42.0, {"labels": {"job": "test"}})

            assert result is True
            mock_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_metric(self):
        """Test querying a metric"""
        config = {"base_url": "http://localhost:8428"}
        storage = VictoriaMetricsStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(
                return_value={
                    "status": "success",
                    "data": {"result": [{"value": ["1234567890", "42.0"]}]},
                }
            )
            mock_client.get = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.retrieve("test_metric")

            assert result == 42.0


class TestLokiStorage:
    """Test Loki storage adapter"""

    @pytest.mark.asyncio
    async def test_store_log(self):
        """Test storing a log entry"""
        config = {"base_url": "http://localhost:3100"}
        storage = LokiStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 204
            mock_client.post = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.store("test_stream", "log message", {"labels": {"job": "test"}})

            assert result is True

    @pytest.mark.asyncio
    async def test_query_logs(self):
        """Test querying logs"""
        config = {"base_url": "http://localhost:3100"}
        storage = LokiStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(
                return_value={
                    "status": "success",
                    "data": {
                        "result": [
                            {"stream": {"job": "test"}, "values": [["1234567890000000000", "log"]]}
                        ]
                    },
                }
            )
            mock_client.get = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.query({"query": '{job="test"}'})

            assert len(result) == 1


class TestTempoStorage:
    """Test Tempo storage adapter"""

    @pytest.mark.asyncio
    async def test_retrieve_trace(self):
        """Test retrieving a trace"""
        config = {"base_url": "http://localhost:3200"}
        storage = TempoStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={"traceID": "12345"})
            mock_client.get = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.retrieve("12345")

            assert result is not None

    @pytest.mark.asyncio
    async def test_search_traces(self):
        """Test searching traces"""
        config = {"base_url": "http://localhost:3200"}
        storage = TempoStorage(config)

        with patch.object(storage, "_client", new=AsyncMock()) as mock_client:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json = MagicMock(return_value={"traces": [{"traceID": "12345"}]})
            mock_client.get = AsyncMock(return_value=mock_response)

            storage._is_initialized = True
            result = await storage.search_traces(service_name="test-service")

            assert len(result) == 1
