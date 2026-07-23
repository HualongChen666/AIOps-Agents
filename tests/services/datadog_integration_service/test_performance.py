# -*- coding: utf-8 -*-
"""Performance benchmark for the Datadog Integration microservice."""

from __future__ import annotations

import asyncio
import time
import uuid

import pytest

import services.datadog_integration_service.config as config_module
from services.datadog_integration_service.metrics import MetricsCollector
from services.datadog_integration_service.service import OPERATIONS, Service

MIN_OPS_PER_SEC = 8000


@pytest.mark.asyncio
@pytest.mark.performance
async def test_operation_throughput():
    """Benchmark in-memory operation throughput."""
    n = 1000
    op = OPERATIONS[0]
    config_module.settings.redis_url = ""
    metrics = MetricsCollector(f"datadog_integration_perf_{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    start = time.perf_counter()
    await asyncio.gather(
        *[
            getattr(service, op)(
                {
                    "config": {"i": i},
                    "idempotency_key": f"perf-{i}",
                }
            )
            for i in range(n)
        ]
    )
    elapsed = time.perf_counter() - start
    ops_per_sec = n / elapsed
    assert (
        ops_per_sec >= MIN_OPS_PER_SEC
    ), f"{op} throughput {ops_per_sec:.0f} ops/s below {MIN_OPS_PER_SEC}"
