# -*- coding: utf-8 -*-
"""Lock and idempotency tests for the Kubernetes Orchestration microservice."""

from __future__ import annotations

import uuid

import pytest

from services.kubernetes_orchestration_service.lock import LockManager
from services.kubernetes_orchestration_service.metrics import MetricsCollector
from services.kubernetes_orchestration_service.service import OPERATIONS, Service


@pytest.mark.asyncio
async def test_idempotency_manager():
    metrics = MetricsCollector(f"kubernetes_orchestration_idemp_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    key = service.idempotency.get_key({"config": {"x": 1}, "idempotency_key": "abc"}, "op1")
    assert key == "op1:abc"
    assert await service.idempotency.is_processed(key) is False
    await service.idempotency.mark_processed(key, {"result": 1})
    assert await service.idempotency.is_processed(key) is True


@pytest.mark.asyncio
async def test_lock_manager_fallback():
    lock = LockManager(redis_url="")
    async with lock.acquire("resource", "req-1"):
        pass


@pytest.mark.asyncio
async def test_service_idempotent_request():
    metrics = MetricsCollector(f"kubernetes_orchestration_idemp_req_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    op = OPERATIONS[0]
    req = {"config": {"test": True}, "idempotency_key": "dup-1"}
    result1 = await getattr(service, op)(req)
    assert result1["success"] is True
    result2 = await getattr(service, op)(req)
    assert result2["success"] is True
    assert result2["status"] == "idempotent"
