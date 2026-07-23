# -*- coding: utf-8 -*-
"""
Test suite for L4 Storage Layer (Phase 1 implementation)
Tests VictoriaMetrics, Loki, and Tempo storage adapters
"""

import asyncio  # noqa: F401
from datetime import datetime, timedelta  # noqa: F401
from unittest.mock import AsyncMock, Mock, patch

import pytest

from core.storage.l4.loki import LokiStorage
from core.storage.l4.storage_manager import L4StorageManager, init_l4_storage_manager  # noqa: F401
from core.storage.l4.tempo import TempoStorage
from core.storage.l4.victoriametrics import VictoriaMetricsStorage


class TestVictoriaMetricsStorage:
    """Test VictoriaMetrics storage adapter"""

    @pytest.fixture
    def vm_config(self):
        return {"base_url": "http://localhost:8428", "timeout": 30}

    @pytest.fixture
    def vm_storage(self, vm_config):
        storage = VictoriaMetricsStorage(vm_config)
        storage.initialize()
        return storage

    def test_initialization(self, vm_config):
        """Test VictoriaMetrics initialization"""
        storage = VictoriaMetricsStorage(vm_config)
        assert storage.name == "victoriametrics"
        assert storage.base_url == "http://localhost:8428"

    @pytest.mark.asyncio
    async def test_store_metric(self, vm_storage):
        """Test storing a metric"""
        with patch.object(vm_storage._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200

            result = await vm_storage.store(
                "cpu.usage_percent",
                75.5,
                {"labels": {"host": "test-server"}, "timestamp": int(datetime.now().timestamp())},
            )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_metrics(self, vm_storage):
        """Test querying metrics"""
        with patch.object(vm_storage._client, "get", new_callable=AsyncMock) as mock_get:
            # Mock the response properly
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={
                    "status": "success",
                    "data": {"result": [{"value": ["1234567890", "75.5"]}]},
                }
            )
            mock_get.return_value = mock_response

            result = await vm_storage.query({"query": "cpu.usage_percent"})

            assert len(result) == 1
            mock_get.assert_called_once()


class TestLokiStorage:
    """Test Loki storage adapter"""

    @pytest.fixture
    def loki_config(self):
        return {"base_url": "http://localhost:3100", "timeout": 30}

    @pytest.fixture
    def loki_storage(self, loki_config):
        storage = LokiStorage(loki_config)
        storage.initialize()
        return storage

    def test_initialization(self, loki_config):
        """Test Loki initialization"""
        storage = LokiStorage(loki_config)
        assert storage.name == "loki"
        assert storage.base_url == "http://localhost:3100"

    @pytest.mark.asyncio
    async def test_store_log(self, loki_storage):
        """Test storing a log entry"""
        with patch.object(loki_storage._client, "post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value.status_code = 200

            result = await loki_storage.store(
                "test-stream",
                "Test log message",
                {
                    "labels": {"level": "info", "service": "test"},
                    "timestamp": int(datetime.now().timestamp() * 1e9),
                },
            )

            assert result is True
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_logs(self, loki_storage):
        """Test querying logs"""
        with patch.object(loki_storage._client, "get", new_callable=AsyncMock) as mock_get:
            # Mock the response properly
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={
                    "status": "success",
                    "data": {"result": [{"stream": {}, "values": [["1234567890", "Test log"]]}]},
                }
            )
            mock_get.return_value = mock_response

            result = await loki_storage.query({"query": '{stream="test-stream"}'})

            assert len(result) == 1
            mock_get.assert_called_once()


class TestTempoStorage:
    """Test Tempo storage adapter"""

    @pytest.fixture
    def tempo_config(self):
        return {"base_url": "http://localhost:3200", "timeout": 30}

    @pytest.fixture
    def tempo_storage(self, tempo_config):
        storage = TempoStorage(tempo_config)
        storage.initialize()
        return storage

    def test_initialization(self, tempo_config):
        """Test Tempo initialization"""
        storage = TempoStorage(tempo_config)
        assert storage.name == "tempo"
        assert storage.base_url == "http://localhost:3200"

    @pytest.mark.asyncio
    async def test_retrieve_trace(self, tempo_storage):
        """Test retrieving a trace"""
        with patch.object(tempo_storage._client, "get", new_callable=AsyncMock) as mock_get:
            # Mock the response properly
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={"traceID": "test-trace-id", "spans": []})
            mock_get.return_value = mock_response

            result = await tempo_storage.retrieve("test-trace-id")

            assert result is not None
            assert result["traceID"] == "test-trace-id"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_traces(self, tempo_storage):
        """Test searching traces"""
        with patch.object(tempo_storage._client, "get", new_callable=AsyncMock) as mock_get:
            # Mock the response properly
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(
                return_value={"traces": [{"traceID": "trace-1"}, {"traceID": "trace-2"}]}
            )
            mock_get.return_value = mock_response

            result = await tempo_storage.search_traces(service_name="test-service", limit=10)

            assert len(result) == 2
            mock_get.assert_called_once()


class TestL4StorageManager:
    """Test L4 Storage Manager"""

    @pytest.fixture
    def l4_config(self):
        return {
            "victoriametrics": {
                "enabled": True,
                "base_url": "http://localhost:8428",
                "timeout": 30,
            },
            "loki": {"enabled": True, "base_url": "http://localhost:3100", "timeout": 30},
            "tempo": {"enabled": True, "base_url": "http://localhost:3200", "timeout": 30},
        }

    def test_initialization(self, l4_config):
        """Test L4 Storage Manager initialization"""
        manager = L4StorageManager(l4_config)
        assert manager.config == l4_config

    @patch("core.storage.l4.storage_manager.VictoriaMetricsStorage")
    @patch("core.storage.l4.storage_manager.LokiStorage")
    @patch("core.storage.l4.storage_manager.TempoStorage")
    def test_initialize_all_backends(self, mock_tempo, mock_loki, mock_vm, l4_config):
        """Test initializing all storage backends"""
        mock_vm_instance = Mock()
        mock_vm_instance.initialize.return_value = True
        mock_vm.return_value = mock_vm_instance

        mock_loki_instance = Mock()
        mock_loki_instance.initialize.return_value = True
        mock_loki.return_value = mock_loki_instance

        mock_tempo_instance = Mock()
        mock_tempo_instance.initialize.return_value = True
        mock_tempo.return_value = mock_tempo_instance

        manager = L4StorageManager(l4_config)
        result = manager.initialize()

        assert result is True
        assert manager._is_initialized is True
        mock_vm.assert_called_once()
        mock_loki.assert_called_once()
        mock_tempo.assert_called_once()

    def test_get_storage_backends(self, l4_config):
        """Test getting storage backends"""
        manager = L4StorageManager(l4_config)

        vm = manager.get_victoriametrics()
        loki = manager.get_loki()
        tempo = manager.get_tempo()

        assert vm is None  # Not initialized yet
        assert loki is None
        assert tempo is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
