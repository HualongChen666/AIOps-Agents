# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core/memory_usage_optimizer.py."""

import asyncio
import gc
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from core.memory_usage_optimizer import (
    MemoryAction,
    MemoryLimit,
    MemorySnapshot,
    MemoryUsageOptimizer,
)


def _snapshot(component: str, used_mb: float, when: datetime) -> MemorySnapshot:
    return MemorySnapshot(
        snapshot_id=f"snap_{component}_{when.isoformat()}",
        timestamp=when,
        total_memory_mb=8192.0,
        used_memory_mb=used_mb,
        available_memory_mb=7000.0,
        memory_percent=12.0,
        gc_objects=1000,
        gc_collections={0: 1, 1: 2, 2: 3},
        metadata={"component": component},
    )


def test_detect_memory_leaks_not_enough_snapshots():
    opt = MemoryUsageOptimizer()
    assert opt.detect_memory_leaks("test") == []


def test_detect_memory_leaks_low_growth():
    opt = MemoryUsageOptimizer()
    now = datetime.now(timezone.utc)
    for i in range(10):
        opt.memory_snapshots.append(
            _snapshot("test", float(i), now - timedelta(minutes=60 - i * 6))
        )
    assert opt.detect_memory_leaks("test") == []


def test_detect_memory_leaks_high_growth():
    opt = MemoryUsageOptimizer()
    now = datetime.now(timezone.utc)
    for i in range(10):
        opt.memory_snapshots.append(
            _snapshot("test", float(i * 100), now - timedelta(minutes=60 - i * 6))
        )
    leaks = opt.detect_memory_leaks("test")
    assert len(leaks) == 1
    assert leaks[0].severity in ("medium", "high")
    assert leaks[0].growth_rate_mb_per_hour > 10


def test_optimize_memory_normal_status():
    opt = MemoryUsageOptimizer()
    opt.set_memory_limit("svc", 1000.0)
    opt.component_memory["svc"] = 100.0
    result = opt.optimize_memory("svc")
    assert result["actions_taken"] == []


def test_optimize_memory_warning_and_leak():
    opt = MemoryUsageOptimizer()
    opt.set_memory_limit(
        "svc",
        100.0,
        warning_threshold_percent=50.0,
        critical_threshold_percent=90.0,
        action_on_exceed=MemoryAction.COLLECT_GARBAGE,
    )
    opt.component_memory["svc"] = 80.0  # 80% usage -> warning

    now = datetime.now(timezone.utc)
    for i in range(10):
        opt.memory_snapshots.append(
            _snapshot("svc", float(i * 100), now - timedelta(minutes=60 - i * 6))
        )

    result = opt.optimize_memory("svc")
    assert "garbage_collection" in result["actions_taken"]
    assert "leak_detection" in result["actions_taken"]
    assert result.get("leaks_detected", 0) >= 1
    assert opt.total_memory_freed_mb != 0.0


def _fake_datetime_class(base_dt: datetime):
    class FakeDateTime:
        @classmethod
        def now(cls, tz=None):
            return base_dt

    return FakeDateTime


def test_get_memory_statistics_no_snapshots():
    opt = MemoryUsageOptimizer()
    opt.memory_snapshots.clear()
    stats = opt.get_memory_statistics()
    assert "total_memory_mb" in stats
    assert "used_memory_mb" in stats
    assert stats["total_gc_collections"] == 0


def _base_dt_for(minute: int) -> datetime:
    return (datetime.now(timezone.utc).replace(minute=minute, second=0, microsecond=0) + timedelta(hours=1))


@pytest.mark.asyncio
async def test_start_monitoring_collect_garbage(monkeypatch):
    import core.memory_usage_optimizer as muo

    monkeypatch.setattr(muo, "datetime", _fake_datetime_class(_base_dt_for(5)))

    opt = MemoryUsageOptimizer({"monitoring_interval_seconds": 10})
    opt.set_memory_limit(
        "svc",
        100.0,
        warning_threshold_percent=50.0,
        critical_threshold_percent=90.0,
        action_on_exceed=MemoryAction.COLLECT_GARBAGE,
    )
    opt.component_memory["svc"] = 90.0  # critical

    await opt.start_monitoring()
    await asyncio.sleep(0.05)

    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t.get_coro().__name__ == "monitoring_loop"
    ]
    assert tasks
    tasks[0].cancel()
    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass

    assert opt.total_gc_collections >= 1


@pytest.mark.asyncio
async def test_start_monitoring_alert_only(monkeypatch):
    import core.memory_usage_optimizer as muo

    monkeypatch.setattr(muo, "datetime", _fake_datetime_class(_base_dt_for(5)))

    opt = MemoryUsageOptimizer({"monitoring_interval_seconds": 10})
    opt.set_memory_limit(
        "svc",
        100.0,
        warning_threshold_percent=50.0,
        critical_threshold_percent=90.0,
        action_on_exceed=MemoryAction.ALERT_ONLY,
    )
    opt.component_memory["svc"] = 90.0

    await opt.start_monitoring()
    await asyncio.sleep(0.05)

    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t.get_coro().__name__ == "monitoring_loop"
    ]
    assert tasks
    tasks[0].cancel()
    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_start_monitoring_no_components(monkeypatch):
    import core.memory_usage_optimizer as muo

    monkeypatch.setattr(muo, "datetime", _fake_datetime_class(_base_dt_for(5)))

    opt = MemoryUsageOptimizer({"monitoring_interval_seconds": 10})
    opt.component_memory.clear()

    await opt.start_monitoring()
    await asyncio.sleep(0.05)

    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t.get_coro().__name__ == "monitoring_loop"
    ]
    assert tasks
    tasks[0].cancel()
    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_start_monitoring_no_limit(monkeypatch):
    import core.memory_usage_optimizer as muo

    monkeypatch.setattr(muo, "datetime", _fake_datetime_class(_base_dt_for(5)))

    opt = MemoryUsageOptimizer({"monitoring_interval_seconds": 10})
    opt.component_memory["svc"] = 90.0
    # no limit configured for svc

    await opt.start_monitoring()
    await asyncio.sleep(0.05)

    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t.get_coro().__name__ == "monitoring_loop"
    ]
    assert tasks
    tasks[0].cancel()
    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass


@pytest.mark.asyncio
async def test_start_monitoring_leak_check_at_minute_zero(monkeypatch):
    import core.memory_usage_optimizer as muo

    monkeypatch.setattr(muo, "datetime", _fake_datetime_class(_base_dt_for(0)))

    opt = MemoryUsageOptimizer({"monitoring_interval_seconds": 10})
    opt.set_memory_limit(
        "svc",
        100.0,
        warning_threshold_percent=50.0,
        critical_threshold_percent=90.0,
        action_on_exceed=MemoryAction.ALERT_ONLY,
    )
    opt.component_memory["svc"] = 90.0

    now = datetime.now(timezone.utc)
    for i in range(10):
        opt.memory_snapshots.append(
            _snapshot("system", float(i * 100), now - timedelta(minutes=60 - i * 6))
        )

    leaks_before = opt.total_leaks_detected

    await opt.start_monitoring()
    await asyncio.sleep(0.05)

    tasks = [
        t
        for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t.get_coro().__name__ == "monitoring_loop"
    ]
    assert tasks
    tasks[0].cancel()
    try:
        await tasks[0]
    except asyncio.CancelledError:
        pass

    assert opt.total_leaks_detected > leaks_before
