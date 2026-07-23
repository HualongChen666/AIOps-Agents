# -*- coding: utf-8 -*-
"""测试 L6 优化执行器"""

import pytest

from core.execution.l6.optimized_executor import (
    ExecutionMetrics,
    OptimizedExecutor,
    get_optimized_executor,
    init_optimized_executor,
)


@pytest.fixture
def executor():
    return OptimizedExecutor(
        {
            "cache_enabled": True,
            "cache_ttl": 1,
            "max_parallel_tasks": 2,
            "l2_integration": False,
            "l3_integration": False,
            "l4_integration": False,
        }
    )


class TestExecutionMetrics:
    def test_record_execution(self):
        m = ExecutionMetrics()
        m.record_execution(True, 1.0)
        m.record_execution(False, 2.0)
        assert m.total_executions == 2
        assert m.get_success_rate() == 0.5

    def test_cache_rates(self):
        m = ExecutionMetrics()
        m.record_cache_hit()
        m.record_cache_miss()
        assert m.get_cache_hit_rate() == 0.5


class TestOptimizedExecutor:
    def test_init(self, executor):
        assert executor._is_initialized is True

    def test_status_and_metrics(self, executor):
        status = executor.get_status()
        assert status["initialized"] is True
        metrics = executor.get_metrics()
        assert metrics["total_executions"] == 0

    @pytest.mark.asyncio
    async def test_execute_with_cache(self, executor, monkeypatch):
        async def handler(params):
            return params["value"]

        result1 = await executor.execute_with_cache("op", {"value": 42}, handler)
        assert result1["success"] is True
        assert result1["result"] == 42
        assert result1["cached"] is False

        cached = {"success": True, "result": 99, "cached": True, "duration": 0.0}
        monkeypatch.setattr(executor, "_get_cached_result", lambda key: cached)

        result2 = await executor.execute_with_cache("op", {"value": 42}, handler)
        assert result2["cached"] is True
        assert result2["result"] == 99

    @pytest.mark.asyncio
    async def test_execute_with_cache_disabled(self):
        executor = OptimizedExecutor({"cache_enabled": False})

        async def handler(params):
            return params["value"]

        result = await executor.execute_with_cache("op", {"value": 42}, handler)
        assert result["result"] == 42

    @pytest.mark.asyncio
    async def test_execute_with_cache_error(self, executor):
        async def handler(params):
            raise ValueError("fail")

        result = await executor.execute_with_cache("op", {}, handler)
        assert result["success"] is False
        assert "fail" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_parallel(self, executor):
        async def handler(params):
            return params["value"]

        tasks = [
            {"operation": "a", "params": {"value": 1}, "handler": handler},
            {"operation": "b", "params": {"value": 2}, "handler": handler},
        ]
        results = await executor.execute_parallel(tasks)
        assert len(results) == 2
        assert all(r["success"] for r in results)

    @pytest.mark.asyncio
    async def test_execute_l2_disabled(self, executor):
        async def handler(params):
            return params["value"]

        result = await executor.execute_with_l2_analysis("op", {"value": 1}, handler)
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_execute_l3_disabled(self, executor):
        result = await executor.execute_with_l3_workflow("wf", {})
        assert result["error"] == "L3 integration not enabled"

    @pytest.mark.asyncio
    async def test_execute_l4_disabled(self, executor):
        await executor.execute_with_l4_storage("op", {}, {})
        assert executor.get_metrics()["total_executions"] == 0

    def test_clear_cache(self, executor):
        executor.cache["key"] = ("value", None)
        executor.clear_cache()
        assert executor.cache == {}

    def test_get_set_cached_result_expired(self, executor):
        import datetime

        old_ts = datetime.datetime.now() - datetime.timedelta(seconds=10)
        executor.cache["k"] = ("v", old_ts)
        assert executor._get_cached_result("k") is None
        assert executor.metrics.cache_misses == 1


class TestFactory:
    def test_init_and_get(self):
        init_optimized_executor({})
        assert get_optimized_executor() is not None
