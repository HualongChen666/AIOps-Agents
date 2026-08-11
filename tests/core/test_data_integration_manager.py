# -*- coding: utf-8 -*-
"""Tests for core/data_integration_manager.py."""

from unittest.mock import AsyncMock

import pytest

from core.data_integration_manager import (
    DataIntegrationManager,
    DataPolicy,
    DataSensitivity,
    DataSource,
    DataStatus,
    DataType,
    get_data_integration_manager,
)


@pytest.fixture
def manager(tmp_path):
    return DataIntegrationManager(config={"storage_dir": str(tmp_path)})


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("core.data_integration_manager.asyncio.sleep", AsyncMock())


@pytest.mark.asyncio
async def test_ingest_and_retrieve(manager):
    record_id = await manager.ingest_data("log_data", {"name": "Alice"})
    assert record_id in manager.data_records
    record = await manager.retrieve_data(record_id, user_id="u1")
    assert record["content"]["name"] == "Alice"
    assert manager.total_access == 1


@pytest.mark.asyncio
async def test_query_data(manager):
    await manager.ingest_data("log_data", {"name": "Alice"})
    results = manager.query_data(source_id="log_data")
    assert len(results) == 1
    results = manager.query_data(sensitivity=DataSensitivity.INTERNAL)
    assert len(results) == 1
    results = manager.query_data(status=DataStatus.ACTIVE, limit=10)
    assert len(results) == 1


@pytest.mark.asyncio
async def test_sync_and_statistics(manager):
    result = await manager.sync_data("user_data")
    assert "sources" in result
    assert result["total_records_synced"] >= 0
    stats = manager.get_statistics()
    assert stats["total_records"] >= 0


def test_register_source_and_policy(manager):
    new_source = DataSource(
        source_id="new",
        source_name="New Source",
        source_type="api",
        data_type=DataType.STRUCTURED,
        endpoint="http://example.com",
        sensitivity=DataSensitivity.INTERNAL,
    )
    manager.register_source(new_source)
    assert "new" in manager.data_sources

    new_policy = DataPolicy(
        policy_id="test_policy",
        policy_name="Test",
        sensitivity=DataSensitivity.INTERNAL,
    )
    manager.register_policy(new_policy)
    assert "test_policy" in manager.data_policies


@pytest.mark.asyncio
async def test_access_handler(manager):
    called = []

    async def handler(record, user_id):
        called.append(user_id)

    manager.register_access_handler(handler)
    record_id = await manager.ingest_data("user_data", {"value": "x"})
    await manager.retrieve_data(record_id, user_id="u2")
    assert called == ["u2"]


def test_get_data_integration_manager():
    mgr = get_data_integration_manager()
    assert isinstance(mgr, DataIntegrationManager)
