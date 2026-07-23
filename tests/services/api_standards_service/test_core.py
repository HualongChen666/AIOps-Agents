# -*- coding: utf-8 -*-
"""Core service tests for the API Standards microservice."""

from __future__ import annotations

import uuid

import pytest

from services.api_standards_service.metrics import MetricsCollector
from services.api_standards_service.service import OPERATIONS, Service


@pytest.mark.asyncio
async def test_all_operations():
    """Test all operation methods."""
    metrics = MetricsCollector(f"api_standards_core_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    for op in OPERATIONS:
        result = await getattr(service, op)({"config": {"test": True}})
        assert result["success"] is True, f"{op} failed: {result}"
        assert result["feature"] == op


@pytest.mark.asyncio
async def test_base_methods_and_state():
    """Test base methods and state management."""
    metrics = MetricsCollector(f"api_standards_core_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    first_op = OPERATIONS[0]
    await getattr(service, first_op)({"config": {"test": True}})
    state = await service.get_state({"config": {"feature": first_op}})
    assert state["success"] is True
    missing = await service.get_state({"config": {"feature": "missing"}})
    assert missing["success"] is False
    backup = await service.backup_state({"config": {"name": "snap1"}})
    assert backup["success"] is True
    restore = await service.restore_state({"config": {"name": "snap1"}})
    assert restore["success"] is True
    restore_missing = await service.restore_state({"config": {"name": "missing"}})
    assert restore_missing["success"] is False
    stats = await service.get_stats()
    assert stats["result"]["index_size"] >= 1
    methods = await service.list_methods()
    assert first_op in methods["result"]["methods"]


@pytest.mark.asyncio
async def test_call_and_unknown_method():
    """Test the generic call dispatcher."""
    metrics = MetricsCollector(f"api_standards_core_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    first_op = OPERATIONS[0]
    result = await service.call(first_op, request={"config": {"test": True}})
    assert result["success"] is True
    with pytest.raises(ValueError):
        await service.call("unknown_method", request={})
