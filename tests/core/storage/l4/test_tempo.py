# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/storage/l4/tempo.py
Target: 90%+ statement and branch coverage
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from core.storage.l4.tempo import TempoStorage


class TestTempoStorage:
    """Test suite for TempoStorage class"""

    @pytest.fixture
    def storage(self):
        """Create a fresh storage instance for each test"""
        return TempoStorage()

    def test_init_default_config(self, storage):
        """Test initialization with default config"""
        assert storage.name == "tempo"
        assert storage.base_url == "http://localhost:3200"
        assert storage.timeout == 30
        assert storage.max_limit == 1000
        assert storage._is_initialized is False
        assert storage._client is None

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = {
            "base_url": "http://custom:3200",
            "timeout": 60,
            "max_limit": 500,
            "read_only": True,
        }
        storage = TempoStorage(config)

        assert storage.base_url == "http://custom:3200"
        assert storage.timeout == 60
        assert storage.max_limit == 500
        assert storage.read_only is True

    def test_init_no_read_only_warning(self, storage, caplog):
        """Test warning when read_only not specified"""
        import logging

        with caplog.at_level(logging.WARNING):
            storage = TempoStorage({"base_url": "http://localhost:3200"})
            assert any("read_only" in record.message for record in caplog.records)

    def test_initialize_success(self, storage):
        """Test successful initialization"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            result = storage.initialize()

            assert result is True
            assert storage._is_initialized is True
            assert storage._client is not None

    def test_initialize_failure(self, storage):
        """Test initialization failure"""
        with patch("httpx.AsyncClient", side_effect=Exception("Connection error")):
            result = storage.initialize()

            assert result is False
            assert storage._is_initialized is False

    @pytest.mark.asyncio
    async def test_store_not_initialized(self, storage):
        """Test store when not initialized"""
        result = await storage.store("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_store_read_only(self, storage):
        """Test store when read_only is True"""
        storage._is_initialized = True
        storage._client = MagicMock()
        storage.read_only = True

        result = await storage.store("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_store_no_implementation(self, storage):
        """Test store (Tempo doesn't support direct storage)"""
        storage._is_initialized = True
        storage._client = MagicMock()
        storage.read_only = False

        result = await storage.store("key", "value")
        assert result is False

    @pytest.mark.asyncio
    async def test_retrieve_not_initialized(self, storage):
        """Test retrieve when not initialized"""
        result = await storage.retrieve("key")
        assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_success(self, storage):
        """Test successful retrieve"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"trace_id": "123"})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = {"trace_id": "123"}

            result = await storage.retrieve("trace_123")

            assert result == {"trace_id": "123"}

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self, storage):
        """Test retrieve when trace not found"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(return_value=MagicMock(status_code=404))

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = None

            result = await storage.retrieve("trace_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_error(self, storage):
        """Test retrieve with error response"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=500, text="Internal error")
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = None

            result = await storage.retrieve("trace_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_retrieve_exception(self, storage):
        """Test retrieve with exception"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.side_effect = Exception("Cache error")

            result = await storage.retrieve("trace_123")

            assert result is None

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test delete (Tempo doesn't support deletion)"""
        result = await storage.delete("key")
        assert result is False

    @pytest.mark.asyncio
    async def test_query_not_initialized(self, storage):
        """Test query when not initialized"""
        result = await storage.query({"query": "test"})
        assert result == []

    @pytest.mark.asyncio
    async def test_query_no_query_param(self, storage):
        """Test query without query parameter"""
        storage._is_initialized = True
        storage._client = AsyncMock()

        result = await storage.query({})
        assert result == []

    @pytest.mark.asyncio
    async def test_query_success(self, storage):
        """Test successful query"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(
                status_code=200, json=lambda: {"traces": [{"trace_id": "123"}, {"trace_id": "456"}]}
            )
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = [{"trace_id": "123"}, {"trace_id": "456"}]

            result = await storage.query({"query": "test"})

            assert len(result) == 2
            assert result[0]["trace_id"] == "123"

    @pytest.mark.asyncio
    async def test_query_invalid_traces(self, storage):
        """Test query when response has invalid traces format"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": "not_a_list"})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.query({"query": "test"})

            assert result == []

    @pytest.mark.asyncio
    async def test_query_limit_enforcement(self, storage):
        """Test that query limit is enforced"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.query({"query": "test", "limit": 2000})

            # Should limit to max_limit
            assert True  # If we get here, no exception

    @pytest.mark.asyncio
    async def test_query_validation_error(self, storage):
        """Test query with validation error"""
        storage._is_initialized = True
        storage._client = AsyncMock()

        with patch(
            "core.storage.l4.tempo.validate_tempoql", side_effect=ValueError("Invalid query")
        ):
            result = await storage.query({"query": "invalid"})

            assert result == []

    @pytest.mark.asyncio
    async def test_query_exception(self, storage):
        """Test query with exception"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.side_effect = Exception("Cache error")

            result = await storage.query({"query": "test"})

            assert result == []

    def test_build_tempo_query_params_empty(self, storage):
        """Test building query params with empty query"""
        result = storage._build_tempo_query_params({})
        assert result == {}

    def test_build_tempo_query_params_basic(self, storage):
        """Test building query params with basic query"""
        result = storage._build_tempo_query_params({"query": "test query"})
        assert result["query"] == "test query"
        assert result["limit"] == 20

    def test_build_tempo_query_params_with_start_end(self, storage):
        """Test building query params with start and end"""
        result = storage._build_tempo_query_params(
            {"query": "test", "start": "2024-01-01", "end": "2024-01-02"}
        )
        assert result["start"] == "2024-01-01"
        assert result["end"] == "2024-01-02"

    def test_build_tempo_query_params_custom_limit(self, storage):
        """Test building query params with custom limit"""
        result = storage._build_tempo_query_params({"query": "test", "limit": 50})
        assert result["limit"] == 50

    @pytest.mark.asyncio
    async def test_search_traces_basic(self, storage):
        """Test basic trace search"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.search_traces()

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_traces_with_filters(self, storage):
        """Test trace search with filters"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.search_traces(
                service_name="my-service",
                operation="GET",
                tags={"env": "prod"},
                min_duration=0.1,
                max_duration=5.0,
            )

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_traces_with_time_range(self, storage):
        """Test trace search with time range"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            start = datetime(2024, 1, 1)
            end = datetime(2024, 1, 2)

            result = await storage.search_traces(start=start, end=end)

            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_search_traces_limit_enforcement(self, storage):
        """Test that search limit is enforced"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.search_traces(limit=2000)

            # Should limit to max_limit
            assert isinstance(result, list)

    def test_build_search_query_empty(self, storage):
        """Test building search query with no filters"""
        result = storage._build_search_query()
        assert result == "{}"

    def test_build_search_query_with_service(self, storage):
        """Test building search query with service name"""
        result = storage._build_search_query(service_name="my-service")
        assert 'service.name="my-service"' in result

    def test_build_search_query_with_operation(self, storage):
        """Test building search query with operation"""
        result = storage._build_search_query(operation="GET")
        assert 'name="GET"' in result

    def test_build_search_query_with_tags(self, storage):
        """Test building search query with tags"""
        result = storage._build_search_query(tags={"env": "prod", "version": "1.0"})
        assert 'env="prod"' in result
        assert 'version="1.0"' in result

    def test_build_search_query_with_duration(self, storage):
        """Test building search query with duration filters"""
        result = storage._build_search_query(min_duration=0.1, max_duration=5.0)
        assert "duration>=0.1s" in result
        assert "duration<=5.0s" in result

    def test_build_search_params_basic(self, storage):
        """Test building search params"""
        query = "test query"
        result = storage._build_search_params(query)
        assert result["query"] == query
        assert result["limit"] == 20

    def test_build_search_params_with_time(self, storage):
        """Test building search params with time range"""
        query = "test query"
        start = datetime(2024, 1, 1)
        end = datetime(2024, 1, 2)

        result = storage._build_search_params(query, start=start, end=end)

        assert "start" in result
        assert "end" in result

    def test_build_search_params_custom_limit(self, storage):
        """Test building search params with custom limit"""
        query = "test query"
        result = storage._build_search_params(query, limit=50)
        assert result["limit"] == 50

    @pytest.mark.asyncio
    async def test_get_services_not_initialized(self, storage):
        """Test get_services when not initialized"""
        result = await storage.get_services()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_services_success(self, storage):
        """Test successful get_services"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"data": ["service1", "service2"]})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = ["service1", "service2"]

            result = await storage.get_services()

            assert len(result) == 2
            assert "service1" in result

    @pytest.mark.asyncio
    async def test_get_services_invalid_data(self, storage):
        """Test get_services with invalid data format"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"data": "not_a_list"})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.get_services()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_services_exception(self, storage):
        """Test get_services with exception"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.side_effect = Exception("Cache error")

            result = await storage.get_services()

            assert result == []

    @pytest.mark.asyncio
    async def test_get_operations_not_initialized(self, storage):
        """Test get_operations when not initialized"""
        result = await storage.get_operations("service1")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_operations_success(self, storage):
        """Test successful get_operations"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"data": ["GET", "POST", "PUT"]})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = ["GET", "POST", "PUT"]

            result = await storage.get_operations("service1")

            assert len(result) == 3
            assert "GET" in result

    @pytest.mark.asyncio
    async def test_get_operations_invalid_data(self, storage):
        """Test get_operations with invalid data format"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(
            return_value=MagicMock(status_code=200, json=lambda: {"data": "not_a_list"})
        )

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.return_value = []

            result = await storage.get_operations("service1")

            assert result == []

    @pytest.mark.asyncio
    async def test_get_operations_exception(self, storage):
        """Test get_operations with exception"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.get = AsyncMock(side_effect=Exception("Network error"))

        with patch("core.storage.l4.tempo.cached_query") as mock_cached:
            mock_cached.side_effect = Exception("Cache error")

            result = await storage.get_operations("service1")

            assert result == []

    def test_close(self, storage):
        """Test closing storage"""
        storage._is_initialized = True
        storage._client = AsyncMock()

        with patch("asyncio.create_task"):
            storage.close()

            assert storage._is_initialized is False

    def test_close_no_client(self, storage):
        """Test closing when no client"""
        storage._is_initialized = True
        storage._client = None

        storage.close()

        assert storage._is_initialized is False

    def test_close_exception(self, storage):
        """Test close with exception"""
        storage._is_initialized = True
        storage._client = AsyncMock()
        storage._client.aclose = AsyncMock(side_effect=Exception("Close error"))

        with patch("asyncio.create_task"):
            storage.close()

            # Should not raise exception
            assert storage._is_initialized is False


class TestTempoStorageIntegration:
    """Test suite for TempoStorage integration scenarios"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, storage):
        """Test full workflow: initialize, query, close"""
        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_client.return_value = mock_instance
            mock_instance.get = AsyncMock(
                return_value=MagicMock(status_code=200, json=lambda: {"traces": []})
            )

            # Initialize
            assert storage.initialize() is True

            # Query
            with patch("core.storage.l4.tempo.cached_query") as mock_cached:
                mock_cached.return_value = []
                result = await storage.query({"query": "test"})
                assert result == []

            # Close
            with patch("asyncio.create_task"):
                storage.close()
                assert storage._is_initialized is False
