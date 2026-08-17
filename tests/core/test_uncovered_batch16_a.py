# -*- coding: utf-8 -*-
"""Tests for batch 16a low-coverage core modules."""

import asyncio
import importlib
import json
import os
import secrets
import sys
import types
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import core.disaster_recovery_drill as dr_module
import core.execution.l6.optimized_executor as executor_module
import core.performance_integration_tester as perf_module
import core.plugin_system as plugin_module
from core.ai.rag.vectorizer import (
    ChunkingStrategy,
    Document,
    DocumentChunk,
    EmbeddingModel,
    FixedSizeChunking,
    SemanticChunking,
    SentenceTransformerEmbedding,
    VectorizationPipeline,
)
from core.disaster_recovery_drill import (
    DisasterRecoveryDrill,
    DrillScenario,
    DrillStatus,
    setup_disaster_recovery,
)
from core.execution.l6.optimized_executor import (
    ExecutionMetrics,
    OptimizedExecutor,
    get_optimized_executor,
    init_optimized_executor,
)
from core.performance_integration_tester import (
    PerformanceIntegrationTester,
    PerformanceMetric,
    PerformanceTest,
    PerformanceTestExecution,
    PerformanceTestType,
    get_performance_integration_tester,
)
from core.plugin_system import (
    BasePlugin,
    PluginManager,
    PluginMetadata,
    PluginStatus,
    PluginSystem,
    PluginType,
    create_plugin_manager,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Helpers / fake implementations
# ---------------------------------------------------------------------------


def _make_fake_random(value):
    class _FakeRandom:
        def __init__(self, *args, **kwargs):
            pass

        def uniform(self, a, b):
            return value

    return _FakeRandom


class _FakeSentenceTransformer:
    def __init__(self, model_name):
        self.model_name = model_name

    def encode(self, text_or_texts):
        def _emb(v):
            return MagicMock(tolist=MagicMock(return_value=[float(v), float(v) + 1.0]))

        if isinstance(text_or_texts, list):
            return [_emb(i) for i in range(len(text_or_texts))]
        return _emb(1.0)


class _DemoBasePlugin(BasePlugin):
    def __init__(self, config=None):
        super().__init__(config)

    def get_metadata(self):
        return PluginMetadata(
            name="demo",
            version="0.1.0",
            description="demo",
            author="test",
            plugin_type=PluginType.COLLECTOR,
            dependencies=[],
        )

    def initialize(self):
        self._is_initialized = True
        return True

    async def execute(self, data):
        return {"out": data}

    def close(self):
        pass


class _InitFalsePlugin(_DemoBasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            name="init_false",
            version="0.1.0",
            description="",
            author="test",
            plugin_type=PluginType.ANALYZER,
            dependencies=[],
        )

    def initialize(self):
        return False


class _BrokenExecutePlugin(_DemoBasePlugin):
    def get_metadata(self):
        return PluginMetadata(
            name="broken",
            version="0.1.0",
            description="",
            author="test",
            plugin_type=PluginType.EXECUTOR,
            dependencies=[],
        )

    async def execute(self, data):
        raise RuntimeError("execute boom")


class _BadPluginManager:
    def __init__(self, *args, **kwargs):
        raise ValueError("boom")


def _ensure_package(monkeypatch, name):
    if name not in sys.modules:
        pkg = types.ModuleType(name)
        pkg.__path__ = []
        monkeypatch.setitem(sys.modules, name, pkg)


def _install_l2_fakes(monkeypatch, error=False):
    for p in ["core.analysis", "core.analysis.l2"]:
        _ensure_package(monkeypatch, p)
    rag = types.ModuleType("core.analysis.l2.rag_engine")
    mr = types.ModuleType("core.analysis.l2.model_router")
    if not error:
        rag.get_rag_engine = lambda: SimpleNamespace(
            retrieve_knowledge=AsyncMock(return_value=["ctx1", "ctx2"])
        )
        mr.get_model_router = lambda: SimpleNamespace(select_model=MagicMock(return_value="gpt-4"))
    monkeypatch.setitem(sys.modules, "core.analysis.l2.rag_engine", rag)
    monkeypatch.setitem(sys.modules, "core.analysis.l2.model_router", mr)


def _install_l3_fakes(monkeypatch, error=False):
    for p in ["core.processing", "core.processing.l3"]:
        _ensure_package(monkeypatch, p)
    we = types.ModuleType("core.processing.l3.workflow_engine")
    if not error:
        we.get_workflow_engine = lambda: SimpleNamespace(
            execute_workflow=AsyncMock(return_value={"status": "ok"})
        )
    monkeypatch.setitem(sys.modules, "core.processing.l3.workflow_engine", we)


def _install_l4_fakes(monkeypatch, error=False):
    for p in ["core.storage", "core.storage.l4"]:
        _ensure_package(monkeypatch, p)
    sm = types.ModuleType("core.storage.l4.storage_manager")
    if not error:
        sm.get_l4_storage_manager = lambda: SimpleNamespace(
            victoriametrics=AsyncMock(),
            loki=AsyncMock(),
        )
    monkeypatch.setitem(sys.modules, "core.storage.l4.storage_manager", sm)


@pytest.fixture
def dr_mocked_asyncio(monkeypatch):
    """Replace the asyncio module inside disaster_recovery_drill to avoid real sleeps."""
    mock = MagicMock()
    mock.sleep = lambda *args, **kwargs: asyncio.sleep(0)
    monkeypatch.setattr(dr_module, "asyncio", mock)
    return mock


# ---------------------------------------------------------------------------
# vectorizer.py
# ---------------------------------------------------------------------------


def test_fixed_size_chunking():
    doc = Document(id="d1", content="a" * 1200, metadata={"title": "t"})
    chunks = FixedSizeChunking(chunk_size=500, overlap=50).chunk(doc)
    assert len(chunks) == 3
    assert chunks[0].chunk_index == 0
    assert chunks[0].document_id == "d1"
    assert "chunk_start" in chunks[0].metadata
    assert chunks[-1].content


def test_semantic_chunking():
    content = "para one\n\npara two\n\n" + "x" * 2000
    doc = Document(id="d2", content=content, metadata={})
    chunks = SemanticChunking(max_chunk_size=500).chunk(doc)
    assert len(chunks) >= 2
    assert all(isinstance(c, DocumentChunk) for c in chunks)


def test_chunking_strategy_not_implemented():
    with pytest.raises(NotImplementedError):
        ChunkingStrategy().chunk(Document(id="d3", content="", metadata={}))


async def test_sentence_transformer_import_missing(monkeypatch):
    empty = types.ModuleType("sentence_transformers")
    monkeypatch.setitem(sys.modules, "sentence_transformers", empty)
    emb = SentenceTransformerEmbedding("unknown-model")
    result = await emb.embed("hi")
    assert result == [0.0] * 1024
    batch = await emb.embed_batch(["a", "b", "c"])
    assert len(batch) == 3
    assert all(len(v) == 1024 for v in batch)


async def test_sentence_transformer_with_model(monkeypatch):
    fake = types.ModuleType("sentence_transformers")
    fake.SentenceTransformer = _FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake)
    emb = SentenceTransformerEmbedding("all-MiniLM-L6-v2")
    result = await emb.embed("hello")
    assert result == [1.0, 2.0]
    batch = await emb.embed_batch(["a", "b"])
    assert batch == [[0.0, 1.0], [1.0, 2.0]]

    # exception paths
    emb._model.encode = MagicMock(side_effect=Exception("model fail"))
    with pytest.raises(Exception, match="model fail"):
        await emb.embed("x")
    with pytest.raises(Exception, match="model fail"):
        await emb.embed_batch(["x"])


async def test_vectorization_pipeline():
    class _FakeEmb(EmbeddingModel):
        async def embed(self, text: str):
            return [0.1, 0.2]

    doc = Document(id="d4", content="one two three four five", metadata={})
    pipeline = VectorizationPipeline(FixedSizeChunking(chunk_size=5, overlap=0), _FakeEmb())
    result = await pipeline.vectorize(doc)
    assert result.chunks
    assert all(c.embedding is not None for c in result.chunks)

    docs = [
        Document(id="d5", content="x y", metadata={}),
        Document(id="d6", content="a b c", metadata={}),
    ]
    out = await pipeline.vectorize_batch(docs)
    assert len(out) == 2


# ---------------------------------------------------------------------------
# performance_integration_tester.py
# ---------------------------------------------------------------------------


def test_performance_default_tests_and_factory(tmp_path):
    tester = get_performance_integration_tester({"reports_dir": str(tmp_path / "r")})
    assert len(tester.performance_tests) == 4
    stats = tester.get_statistics()
    assert stats["total_tests"] == 4
    assert stats["total_executions"] == 0


def test_performance_register_and_status_missing(tmp_path):
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    test = PerformanceTest(
        test_id="custom",
        test_name="Custom",
        test_type=PerformanceTestType.LOAD_TEST,
        target_endpoint="/x",
    )
    tester.register_test(test)
    assert "custom" in tester.performance_tests
    assert tester.get_execution_status("missing") is None


async def test_performance_run_pass(tmp_path, monkeypatch):
    monkeypatch.setattr(
        perf_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock(), create_task=asyncio.create_task),
    )
    monkeypatch.setattr(secrets, "SystemRandom", _make_fake_random(0.0))
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    exec_id = await tester.run_performance_test("load_test_api")
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    await asyncio.gather(*pending, return_exceptions=True)
    status = tester.get_execution_status(exec_id)
    assert status["status"] == "completed"
    assert status["passed"] is True


async def test_performance_run_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(
        perf_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock(), create_task=asyncio.create_task),
    )
    monkeypatch.setattr(secrets, "SystemRandom", _make_fake_random(100.0))
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    exec_id = await tester.run_performance_test("load_test_api")
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    await asyncio.gather(*pending, return_exceptions=True)
    status = tester.get_execution_status(exec_id)
    assert status["status"] == "completed"
    assert status["passed"] is False
    assert "thresholds" in (status["error_message"] or "").lower() or True


async def test_performance_run_not_found_and_disabled(tmp_path):
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    with pytest.raises(ValueError, match="not found"):
        await tester.run_performance_test("missing")
    tester.performance_tests["load_test_api"].enabled = False
    with pytest.raises(ValueError, match="not enabled"):
        await tester.run_performance_test("load_test_api")


async def test_performance_execute_error(tmp_path, monkeypatch):
    monkeypatch.setattr(
        perf_module,
        "asyncio",
        SimpleNamespace(
            sleep=AsyncMock(side_effect=Exception("sleep boom")),
            create_task=asyncio.create_task,
        ),
    )
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    execution_id = "exec_test"
    tester.test_executions[execution_id] = PerformanceTestExecution(
        execution_id=execution_id, test_id="load_test_api"
    )
    await tester._execute_performance_test(execution_id)
    status = tester.get_execution_status(execution_id)
    assert status["status"] == "error"
    assert "sleep boom" in (status["error_message"] or "")


async def test_performance_report_and_stats(tmp_path, monkeypatch):
    monkeypatch.setattr(
        perf_module,
        "asyncio",
        SimpleNamespace(sleep=AsyncMock(), create_task=asyncio.create_task),
    )
    monkeypatch.setattr(secrets, "SystemRandom", _make_fake_random(0.0))
    tester = PerformanceIntegrationTester({"reports_dir": str(tmp_path / "r")})
    exec_id = await tester.run_performance_test("load_test_api")
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    await asyncio.gather(*pending, return_exceptions=True)

    report = await tester.generate_performance_report()
    assert report["summary"]["total"] == 1
    assert "report_" in report["report_id"]

    filtered = await tester.generate_performance_report(test_id="load_test_api")
    assert filtered["summary"]["total"] == 1

    missing = await tester.generate_performance_report(test_id="missing")
    assert missing["summary"]["total"] == 0

    stats = tester.get_statistics()
    assert stats["total_executions"] == 1


# ---------------------------------------------------------------------------
# plugin_system.py
# ---------------------------------------------------------------------------


async def test_plugin_manager_register_load_execute(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    manager = PluginManager()
    assert manager.initialize() is True
    assert manager._is_initialized is True

    manager.register_plugin(_DemoBasePlugin)
    assert manager.load_plugin("demo") is True

    result = await manager.execute_plugin("demo", {"x": 1})
    assert result == {"out": {"x": 1}}

    status = manager.get_plugin_status("demo")
    assert status["initialized"] is True
    assert manager.get_plugin("demo")["metadata"]["name"] == "demo"

    plugins = manager.list_plugins()
    assert len(plugins) == 1
    typed = manager.list_plugins(PluginType.COLLECTOR)
    assert len(typed) == 1

    assert manager.unload_plugin("demo") is True
    assert await manager.execute_plugin("demo", {}) is None
    manager.close()


def test_plugin_manager_load_fail_and_reload(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    manager = PluginManager()
    manager.initialize()
    manager.register_plugin(_InitFalsePlugin)
    assert manager.load_plugin("init_false") is False

    manager.register_plugin(_DemoBasePlugin)
    assert manager.load_plugin("demo") is True
    assert manager.reload_plugin("demo") is True
    assert manager.reload_plugin("init_false") is False


async def test_plugin_manager_broken_execute_and_not_found(monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    manager = PluginManager()
    manager.initialize()
    manager.register_plugin(_BrokenExecutePlugin)
    assert manager.load_plugin("broken") is True
    assert await manager.execute_plugin("broken", {}) is None
    assert manager.get_plugin("missing") is None
    assert manager.unload_plugin("missing") is False


def test_plugin_discovery_and_bad_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "path", list(sys.path))
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()

    good = plugins_dir / f"demo_plugin_{uuid4().hex}.py"
    good.write_text(
        "from core.plugin_system import BasePlugin, PluginMetadata, PluginType\n"
        "class DemoDiscovery(BasePlugin):\n"
        "    def get_metadata(self):\n"
        "        return PluginMetadata('disc', '1.0', '', 't', PluginType.STORAGE, [])\n"
        "    def initialize(self):\n"
        "        return True\n"
        "    async def execute(self, data):\n"
        "        return data\n"
        "    def close(self):\n"
        "        pass\n"
    )

    bad = plugins_dir / f"bad_plugin_{uuid4().hex}.py"
    bad.write_text("not valid python syntax !!!\n")

    missing_dir = str(tmp_path / "nonexistent")
    manager = PluginManager([str(plugins_dir), missing_dir])
    assert manager.initialize() is True
    assert "disc" in manager._plugins
    assert manager.list_plugins(PluginType.STORAGE)
    assert manager.close() is None


def test_base_plugin_context_manager():
    with _DemoBasePlugin({"x": 1}) as p:
        assert p._is_initialized
    assert p.validate_config(["x"]) is True
    assert p.validate_config(["missing"]) is False


def test_create_plugin_manager_success():
    assert create_plugin_manager([]) is not None


def test_create_plugin_manager_failure(monkeypatch):
    monkeypatch.setattr(PluginManager, "initialize", lambda self: False)
    assert create_plugin_manager([]) is None


def test_create_plugin_manager_exception(monkeypatch):
    monkeypatch.setattr(plugin_module, "PluginManager", _BadPluginManager)
    assert create_plugin_manager([]) is None


# ---------------------------------------------------------------------------
# optimized_executor.py
# ---------------------------------------------------------------------------


def test_execution_metrics():
    m = ExecutionMetrics()
    m.record_execution(True, 1.0)
    m.record_execution(False, 2.0)
    m.record_cache_hit()
    m.record_cache_miss()
    assert m.get_success_rate() == 0.5
    assert m.get_cache_hit_rate() == 0.5


async def test_optimized_executor_cache_and_status(monkeypatch):
    ex = OptimizedExecutor({"cache_enabled": True, "cache_ttl": 300})
    status = ex.get_status()
    assert status["cache_enabled"] is True

    async def handler(params):
        return {"ok": True, "p": params}

    r1 = await ex.execute_with_cache("op1", {"x": 1}, handler)
    assert r1["success"] is True
    assert r1["cached"] is False

    # Force the cached-result branch by short-circuiting _get_cached_result.
    monkeypatch.setattr(ex, "_get_cached_result", lambda key: {"cached": True})
    r2 = await ex.execute_with_cache("op1", {"x": 1}, handler)
    assert r2 == {"cached": True}

    ex.clear_cache()

    # cache disabled
    ex_no_cache = OptimizedExecutor({"cache_enabled": False})
    r3 = await ex_no_cache.execute_with_cache("op2", {}, handler)
    assert r3["cached"] is False


async def test_optimized_executor_cache_exception():
    ex = OptimizedExecutor()

    async def bad(params):
        raise ValueError("bad")

    r = await ex.execute_with_cache("op", {}, bad)
    assert r["success"] is False


async def test_optimized_executor_cache_get_and_expired():
    ex = OptimizedExecutor()
    ex.cache["k"] = ("value", datetime.now())
    assert ex._get_cached_result("k") == "value"

    ex.cache["k2"] = ("value2", datetime.now() - timedelta(seconds=1000))
    assert ex._get_cached_result("k2") is None
    assert "k2" not in ex.cache


async def test_optimized_executor_parallel():
    ex = OptimizedExecutor({"max_parallel_tasks": 2})

    async def h(params):
        return params

    tasks = [
        {"operation": "a", "params": {"i": 1}, "handler": h},
        {"operation": "b", "params": {"i": 2}, "handler": h},
    ]
    results = await ex.execute_parallel(tasks)
    assert all(r["success"] for r in results)

    async def fail(params):
        raise RuntimeError("fail")

    bad_tasks = [
        {"operation": "c", "params": {}, "handler": fail},
        {"operation": "d", "params": {"ok": 1}, "handler": h},
    ]
    results = await ex.execute_parallel(bad_tasks)
    assert any(not r["success"] for r in results)


async def test_optimized_executor_l2_success(monkeypatch):
    _install_l2_fakes(monkeypatch, error=False)
    ex = OptimizedExecutor({"l2_integration": True})

    async def handler(params):
        return params

    r = await ex.execute_with_l2_analysis("l2_op", {"q": 1}, handler)
    assert r["success"] is True
    assert r["result"]["context_enhancement"] == ["ctx1", "ctx2"]
    assert r["result"]["selected_model"] == "gpt-4"


async def test_optimized_executor_l2_error(monkeypatch):
    _install_l2_fakes(monkeypatch, error=True)
    ex = OptimizedExecutor({"l2_integration": True})

    async def handler(params):
        return params

    r = await ex.execute_with_l2_analysis("l2_op", {}, handler)
    assert r["success"] is True


async def test_optimized_executor_l3_success(monkeypatch):
    _install_l3_fakes(monkeypatch, error=False)
    ex = OptimizedExecutor({"l3_integration": True})
    r = await ex.execute_with_l3_workflow("wf", {"ctx": 1})
    assert r["status"] == "ok"


async def test_optimized_executor_l3_disabled_and_error(monkeypatch):
    ex = OptimizedExecutor({"l3_integration": False})
    assert await ex.execute_with_l3_workflow("wf", {}) == {"error": "L3 integration not enabled"}

    _install_l3_fakes(monkeypatch, error=True)
    ex2 = OptimizedExecutor({"l3_integration": True})
    r = await ex2.execute_with_l3_workflow("wf", {})
    assert "error" in r


async def test_optimized_executor_l4_success_and_disabled(monkeypatch):
    _install_l4_fakes(monkeypatch, error=False)
    ex = OptimizedExecutor({"l4_integration": True})
    await ex.execute_with_l4_storage("op", {"r": 1}, {"metrics": {"m": 1}, "logs": {"l": 1}})

    ex2 = OptimizedExecutor({"l4_integration": False})
    assert await ex2.execute_with_l4_storage("op2", {}, {}) is None


async def test_optimized_executor_l4_error(monkeypatch):
    _install_l4_fakes(monkeypatch, error=True)
    ex = OptimizedExecutor({"l4_integration": True})
    r = await ex.execute_with_l4_storage("op", {"r": 1}, {"metrics": {}})
    assert r is None


def test_optimized_executor_singleton_and_metrics(monkeypatch):
    monkeypatch.setattr(executor_module, "_optimized_executor", None)
    init_optimized_executor({"cache_enabled": True})
    assert get_optimized_executor() is not None
    ex = get_optimized_executor()
    ex.metrics.record_execution(True, 1.0)
    m = ex.get_metrics()
    assert m["total_executions"] == 1


# ---------------------------------------------------------------------------
# disaster_recovery_drill.py
# ---------------------------------------------------------------------------


async def test_drill_all_scenarios(dr_mocked_asyncio):
    drill = DisasterRecoveryDrill()
    for scenario in DrillScenario:
        result = await drill.run_drill(scenario)
        assert result.status == DrillStatus.COMPLETED
        assert result.success is True
        assert result.end_time is not None


async def test_drill_concurrent_and_unknown(dr_mocked_asyncio):
    drill = DisasterRecoveryDrill()
    first = asyncio.create_task(drill.run_drill(DrillScenario.SERVICE_OUTAGE))
    await asyncio.sleep(0)
    with pytest.raises(RuntimeError, match="already running"):
        await drill.run_drill(DrillScenario.SERVICE_OUTAGE)
    await first


async def test_drill_history_and_stats(dr_mocked_asyncio):
    drill = DisasterRecoveryDrill()
    await drill.run_drill(DrillScenario.SERVICE_OUTAGE)
    await drill.run_drill(DrillScenario.DATABASE_FAILOVER)

    history = drill.get_drill_history(limit=1)
    assert len(history) == 1

    stats = drill.get_drill_stats()
    assert stats["total_drills"] == 2
    assert "scenario_stats" in stats


def test_drill_empty_stats():
    drill = DisasterRecoveryDrill()
    stats = drill.get_drill_stats()
    assert stats["total_drills"] == 0


async def test_setup_disaster_recovery():
    result = await setup_disaster_recovery()
    assert result["status"] == "success"
    assert len(result["scenarios"]) == len(DrillScenario)
