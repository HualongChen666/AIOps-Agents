# -*- coding: utf-8 -*-
"""Tests for the auto-heal statistics average-execution-time computation.

Guards against regression to the old hard-coded ``120.5`` placeholder: the
value must now come from persisted ``RepairRecord`` history.
"""

from __future__ import annotations

from api import autoheal_router as ar


async def test_avg_execution_time_is_mean_of_real_records(monkeypatch):
    async def fake_query(today_only=False, limit=10):
        return [
            {"repair_duration_sec": 10.0},
            {"repair_duration_sec": 30.0},
            {"repair_duration_sec": None},  # must be ignored
            {"repair_duration_sec": 20.0},
        ]

    monkeypatch.setattr(ar, "async_query_repairs", fake_query)
    assert await ar._compute_average_execution_time() == 20.0


async def test_avg_execution_time_returns_zero_without_history(monkeypatch):
    async def fake_query(today_only=False, limit=10):
        return []

    monkeypatch.setattr(ar, "async_query_repairs", fake_query)
    assert await ar._compute_average_execution_time() == 0.0


async def test_avg_execution_time_handles_missing_query_fn(monkeypatch):
    monkeypatch.setattr(ar, "async_query_repairs", None)
    assert await ar._compute_average_execution_time() == 0.0


async def test_avg_execution_time_swallows_query_errors(monkeypatch):
    async def boom(today_only=False, limit=10):
        raise RuntimeError("db down")

    monkeypatch.setattr(ar, "async_query_repairs", boom)
    assert await ar._compute_average_execution_time() == 0.0
