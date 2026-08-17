# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 12-c modules."""

import json
import sys
import types
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.ai.rag.knowledge_base
# ---------------------------------------------------------------------------
@pytest.fixture
def kb_module():
    import core.ai.rag.knowledge_base as kb

    return kb


@pytest.fixture
def vectorized_doc_factory():
    from core.ai.rag.vectorizer import Document, DocumentChunk

    def _make(doc_id, chunks=None, content="hello"):
        if chunks is None:
            chunks = [
                DocumentChunk(
                    id=f"{doc_id}_chunk_0",
                    document_id=doc_id,
                    content="chunk zero",
                    chunk_index=0,
                    metadata={"src": "test"},
                    embedding=[0.1, 0.2],
                )
            ]
        return Document(id=doc_id, content=content, metadata={"source": "test"}, chunks=chunks)

    return _make


@pytest.mark.asyncio
async def test_kb_add_document_uses_upsert_points(kb_module, vectorized_doc_factory):
    pipeline = AsyncMock()
    pipeline.vectorize = AsyncMock(return_value=vectorized_doc_factory("d1"))
    store = MagicMock()
    store.upsert_points = MagicMock()
    store.upsert = MagicMock()

    kb = kb_module.KnowledgeBase("kb1", pipeline, store)
    result = await kb.add_document("d1", "hello world")

    assert result.id == "d1"
    assert "d1" in kb.documents
    assert store.upsert_points.called
    assert not store.upsert.called
    pipeline.vectorize.assert_awaited_once()


@pytest.mark.asyncio
async def test_kb_store_with_qdrant_point_struct(kb_module, vectorized_doc_factory, monkeypatch):
    pipeline = AsyncMock()
    pipeline.vectorize = AsyncMock(return_value=vectorized_doc_factory("d2"))

    class FakeStore:
        upsert = MagicMock()

    fake_point = lambda **kw: {  # noqa: E731
        "qdrant": True,
        "id": kw.get("id"),
        "vector": kw.get("vector"),
        "payload": kw.get("payload"),
    }
    qdrant_models = types.SimpleNamespace(PointStruct=fake_point)
    qdrant_client_pkg = types.SimpleNamespace(models=qdrant_models)
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_client_pkg)
    monkeypatch.setitem(sys.modules, "qdrant_client.models", qdrant_models)

    store = FakeStore()
    kb = kb_module.KnowledgeBase("kb2", pipeline, store)
    await kb.add_document("d2", "hello again")

    assert store.upsert.called
    call = store.upsert.call_args.kwargs
    assert call.get("collection_name") == "kb2"
    assert isinstance(call.get("points"), list)
    assert call["points"][0].get("qdrant") is True


@pytest.mark.asyncio
async def test_kb_store_upsert_raw_points_fallback(kb_module, vectorized_doc_factory, monkeypatch):
    pipeline = AsyncMock()
    pipeline.vectorize = AsyncMock(return_value=vectorized_doc_factory("d2b"))

    class FakeStore:
        upsert = MagicMock()

    # Force the qdrant PointStruct import to fail so the raw-points fallback is used.
    qdrant_models = types.SimpleNamespace()
    qdrant_client_pkg = types.SimpleNamespace(models=qdrant_models)
    monkeypatch.setitem(sys.modules, "qdrant_client", qdrant_client_pkg)
    monkeypatch.setitem(sys.modules, "qdrant_client.models", qdrant_models)

    store = FakeStore()
    kb = kb_module.KnowledgeBase("kb2b", pipeline, store)
    await kb.add_document("d2b", "hello again")

    assert store.upsert.called
    call = store.upsert.call_args.kwargs
    assert call.get("collection_name") == "kb2b"
    assert isinstance(call.get("points"), list)
    assert call["points"][0]["id"].endswith("_chunk_0")


@pytest.mark.asyncio
async def test_kb_store_exception_and_skips_missing_embeddings(kb_module, vectorized_doc_factory):
    from core.ai.rag.vectorizer import DocumentChunk

    # Exception during upsert should not break add_document
    class BoomStore:
        upsert_points = MagicMock(side_effect=RuntimeError("upsert boom"))

    pipeline = AsyncMock()
    doc_ok = vectorized_doc_factory("d3")
    pipeline.vectorize = AsyncMock(return_value=doc_ok)
    kb = kb_module.KnowledgeBase("kb3", pipeline, BoomStore())
    result = await kb.add_document("d3", "hello")
    assert result.id == "d3"
    assert "d3" in kb.documents

    # Chunks with no embedding should be skipped
    class FakeStore:
        upsert = MagicMock()

    chunk_no_emb = DocumentChunk(
        id="d4_chunk_0",
        document_id="d4",
        content="no emb",
        chunk_index=0,
        metadata={},
        embedding=None,
    )
    doc_no_emb = vectorized_doc_factory("d4", chunks=[chunk_no_emb])
    pipeline.vectorize = AsyncMock(return_value=doc_no_emb)
    kb = kb_module.KnowledgeBase("kb4", pipeline, FakeStore())
    await kb.add_document("d4", "hello")
    FakeStore.upsert.assert_not_called()


@pytest.mark.asyncio
async def test_kb_delete_get_list_and_batch(kb_module, vectorized_doc_factory):
    pipeline = AsyncMock()
    pipeline.vectorize = AsyncMock(
        side_effect=lambda d: vectorized_doc_factory(d.id, content=d.content)
    )

    kb = kb_module.KnowledgeBase("kb5", pipeline, None)
    batch = [
        {"id": "b1", "content": "one"},
        {"id": "b2", "content": "two"},
    ]
    results = await kb.add_documents_batch(batch)
    assert len(results) == 2
    assert kb.list_documents() == ["b1", "b2"]

    assert kb.get_document("b1").id == "b1"
    assert kb.get_document("missing") is None

    assert await kb.delete_document("b1") is True
    assert await kb.delete_document("b1") is False
    assert kb.list_documents() == ["b2"]


# ---------------------------------------------------------------------------
# core.websocket_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def ws_module():
    import core.websocket_manager as wm

    return wm


class FakeWebSocket:
    def __init__(self, fail_send=False):
        self.accept = AsyncMock()
        self.send_json = AsyncMock(side_effect=RuntimeError("closed") if fail_send else None)


@pytest.mark.asyncio
async def test_ws_connect_disconnect_and_metrics(ws_module, monkeypatch):
    exporter = MagicMock()
    exporter.record_websocket_connections = MagicMock()
    monkeypatch.setattr(ws_module, "get_metrics_exporter", lambda: exporter)

    manager = ws_module.ConnectionManager()
    ws = FakeWebSocket()

    await manager.connect(ws, "ops")
    assert ws in manager.active_connections["ops"]
    assert manager.get_connection_count("ops") == 1
    exporter.record_websocket_connections.assert_called_with("ops", 1)

    manager.disconnect(ws, "ops")
    assert manager.get_connection_count("ops") == 0
    assert ws not in manager.active_connections.get("ops", set())


@pytest.mark.asyncio
async def test_ws_connect_metrics_exception(ws_module, monkeypatch):
    exporter = MagicMock()
    exporter.record_websocket_connections = MagicMock(side_effect=RuntimeError("metrics boom"))
    monkeypatch.setattr(ws_module, "get_metrics_exporter", lambda: exporter)

    manager = ws_module.ConnectionManager()
    ws = FakeWebSocket()
    await manager.connect(ws, "ops")
    assert manager.get_connection_count("ops") == 1


@pytest.mark.asyncio
async def test_ws_broadcast_and_cleanup(ws_module, monkeypatch):
    monkeypatch.setattr(ws_module, "get_metrics_exporter", lambda: MagicMock())

    manager = ws_module.ConnectionManager()
    good = FakeWebSocket()
    bad = FakeWebSocket(fail_send=True)

    await manager.connect(good, "ops")
    await manager.connect(bad, "ops")
    assert manager.get_connection_count("ops") == 2

    await manager.broadcast({"msg": "hi"}, "ops")
    good.send_json.assert_awaited()
    bad.send_json.assert_awaited()
    assert bad not in manager.active_connections["ops"]
    assert good in manager.active_connections["ops"]

    # Unknown channel should return immediately
    await manager.broadcast({"msg": "x"}, "unknown")
    assert manager.get_connection_count("unknown") == 0


@pytest.mark.asyncio
async def test_ws_send_personal_message(ws_module):
    manager = ws_module.ConnectionManager()
    ws = FakeWebSocket()
    await manager.send_personal_message({"hello": "world"}, ws)
    ws.send_json.assert_awaited_once()

    ws.send_json = AsyncMock(side_effect=RuntimeError("send failed"))
    await manager.send_personal_message({"hello": "world"}, ws)
    ws.send_json.assert_awaited()


def test_ws_global_manager(ws_module):
    assert isinstance(ws_module.manager, ws_module.ConnectionManager)


# ---------------------------------------------------------------------------
# core.ai_enhancement
# ---------------------------------------------------------------------------
@pytest.fixture
def ae_module():
    import core.ai_enhancement as ae

    return ae


@pytest.fixture
def enhancer(ae_module):
    return ae_module.AIAnalysisEnhancer()


@pytest.fixture
def conv_mgr(ae_module):
    return ae_module.MultiTurnConversationManager()


def test_ae_generate_context_key(enhancer):
    data = {
        "host": "h1",
        "platform": "linux",
        "level": "critical",
        "message": "disk full",
    }
    key1 = enhancer.generate_context_key(data)
    key2 = enhancer.generate_context_key(data)
    assert key1 == key2
    assert len(key1) == 64


def test_ae_cache_hit_miss_and_expiry(enhancer):
    analysis = {"root_cause": "cpu", "confidence": 0.9}
    enhancer.cache_analysis("k1", analysis)
    assert enhancer.get_cached_analysis("k1") == analysis
    assert enhancer.get_cached_analysis("missing") is None

    enhancer._context_cache["old"] = {
        "analysis": {"x": 1},
        "timestamp": (datetime.now(timezone.utc) - timedelta(seconds=4000)).isoformat(),
    }
    assert enhancer.get_cached_analysis("old") is None
    assert "old" not in enhancer._context_cache


def test_ae_invalidate_cache(enhancer):
    enhancer.cache_analysis("a", {"ok": 1})
    enhancer.cache_analysis("b", {"ok": 2})
    enhancer.invalidate_cache("a")
    assert "a" not in enhancer._context_cache
    assert "b" in enhancer._context_cache
    enhancer.invalidate_cache()
    assert not enhancer._context_cache


def test_ae_record_analysis_and_history(enhancer):
    for i in range(3):
        enhancer.record_analysis({"id": i})
    assert len(enhancer.get_analysis_history()) == 3
    assert [a["id"] for a in enhancer.get_analysis_history(2)] == [1, 2]
    assert len(enhancer.get_analysis_history(100)) == 3
    assert enhancer.__class__().get_analysis_history(5) == []

    enhancer._analysis_history = [{"id": i} for i in range(1002)]
    enhancer.record_analysis({"id": 1002})
    assert len(enhancer._analysis_history) == 1000
    assert enhancer._analysis_history[-1]["id"] == 1002


def test_ae_performance_metrics(enhancer):
    enhancer.update_performance_metrics({"success": True, "response_time": 1.0, "model": "gpt-4"})
    enhancer.update_performance_metrics({"success": False, "response_time": 2.0, "model": "gpt-4"})
    enhancer.update_performance_metrics({"success": True, "response_time": 3.0})

    metrics = enhancer.get_performance_metrics()
    assert metrics["total_analyses"] == 3
    assert metrics["successful_analyses"] == 2
    assert metrics["failed_analyses"] == 1
    assert metrics["model_usage"]["gpt-4"] == 2
    assert metrics["model_usage"]["unknown"] == 1
    assert metrics["average_response_time"] == pytest.approx(2.0)
    assert "success_rate" in metrics
    assert "cache_hit_rate" in metrics
    assert "timestamp" in metrics

    # Empty metrics path
    fresh = enhancer.__class__()
    empty = fresh.get_performance_metrics()
    assert empty["success_rate"] == "0.00%"
    assert empty["cache_hit_rate"] == 0.0


def test_ae_context_suggestions(enhancer):
    alert = {
        "host": "h",
        "platform": "k8s",
        "level": "critical",
        "message": "m",
    }
    key = enhancer.generate_context_key(alert)
    enhancer.record_analysis({"context_key": key})
    suggestions = enhancer.get_context_suggestions(alert)
    assert any("similar" in s for s in suggestions)
    assert any("k8s" in s for s in suggestions)
    assert any("High severity" in s for s in suggestions)

    plain = {"host": "h", "level": "warning", "message": "m"}
    suggestions2 = enhancer.get_context_suggestions(plain)
    assert not any("Platform-specific" in s for s in suggestions2)
    assert not any("High severity" in s for s in suggestions2)


def test_ae_multi_turn_conversation(conv_mgr):
    conv_mgr.create_conversation("c1")
    conv_mgr.add_message("c1", "user", "hello")
    conv_mgr.add_message("c1", "assistant", "hi", {"model": "gpt"})

    history = conv_mgr.get_conversation_history("c1", limit=2)
    assert len(history) == 2
    assert history[0]["role"] == "user"

    # Auto-creates missing conversation
    conv_mgr.add_message("c2", "user", "auto")
    assert "c2" in conv_mgr._conversations

    context = conv_mgr.get_conversation_context("c1")
    assert "user: hello" in context
    assert "assistant: hi" in context

    assert conv_mgr.get_conversation_history("missing") == []
    assert conv_mgr.get_conversation_context("missing") == ""

    # Cleanup old and empty conversations
    conv_mgr._conversations["old"] = [
        {
            "role": "user",
            "content": "x",
            "metadata": {},
            "timestamp": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
        }
    ]
    conv_mgr._conversations["empty"] = []
    conv_mgr.cleanup_expired_conversations()
    assert "old" not in conv_mgr._conversations
    assert "empty" not in conv_mgr._conversations
    assert "c1" in conv_mgr._conversations


def test_ae_global_accessors(ae_module):
    assert isinstance(ae_module.get_ai_enhancer(), ae_module.AIAnalysisEnhancer)
    assert isinstance(ae_module.get_conversation_manager(), ae_module.MultiTurnConversationManager)


# ---------------------------------------------------------------------------
# core.localization_resource_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def lrm_module():
    import core.localization_resource_manager as lrm

    return lrm


@pytest.fixture
def lrm(lrm_module):
    return lrm_module.LocalizationResourceManager()


def test_lrm_defaults_and_summary(lrm, lrm_module):
    assert lrm.get_translations("en", "common")["welcome"] == "Welcome"
    assert lrm.get_translations("zh", "errors")["server_error"] == "服务器错误"

    summary = lrm.get_resource_summary()
    assert summary["total_languages"] == 3
    assert "common" in summary["namespaces"]
    assert "errors" in summary["namespaces"]
    assert summary["registered_files"] == 0
    assert isinstance(lrm_module.get_resource_manager(), lrm_module.LocalizationResourceManager)


def test_lrm_register_and_load_resource_file(lrm, tmp_path):
    ns_file = tmp_path / "new.json"
    ns_file.write_text(json.dumps({"key1": "value1", "key2": "value2"}), encoding="utf-8")

    assert lrm.register_resource_file("en", "newns", str(ns_file), "1.0") is True
    assert lrm.register_resource_file("en", "newns", str(ns_file), "1.1") is False
    assert lrm.load_resource_file("en", "newns") is True
    assert lrm.get_translations("en", "newns") == {
        "key1": "value1",
        "key2": "value2",
    }
    assert lrm.load_resource_file("en", "missing") is False

    bad = tmp_path / "bad.json"
    bad.write_text("not-json", encoding="utf-8")
    assert lrm.register_resource_file("en", "badns", str(bad)) is True
    assert lrm.load_resource_file("en", "badns") is False


def test_lrm_get_translations(lrm):
    assert lrm.get_translations("xx", "common") is None
    assert lrm.get_translations("en", "xx") is None


def test_lrm_add_translation(lrm):
    assert lrm.add_translation("fr", "common", "hello", "Bonjour") is True
    assert lrm.get_translations("fr", "common")["hello"] == "Bonjour"
    assert lrm.add_translation("fr", "common", "hello", "Salut") is True
    assert lrm.get_translations("fr", "common")["hello"] == "Salut"


def test_lrm_export_and_import_translations(lrm, tmp_path):
    out = tmp_path / "out.json"
    assert lrm.export_translations("en", "common", str(out)) is True
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["welcome"] == "Welcome"

    assert lrm.export_translations("en", "missing", str(out)) is False

    imp = tmp_path / "import.json"
    imp.write_text(json.dumps({"new": "NewValue"}), encoding="utf-8")
    assert lrm.import_translations("es", "common", str(imp)) is True
    assert lrm.get_translations("es", "common")["new"] == "NewValue"
    assert lrm.import_translations("es", "common", str(tmp_path / "nonexistent.json")) is False


def test_lrm_get_missing_translations(lrm):
    lrm._add_translations_to_cache("src", "ns", {"a": "1", "b": "2"})

    missing = lrm.get_missing_translations("src", "tgt", "ns")
    assert set(missing) == {"a", "b"}

    lrm._add_translations_to_cache("tgt", "ns", {"a": "X"})
    missing = lrm.get_missing_translations("src", "tgt", "ns")
    assert missing == ["b"]

    assert lrm.get_missing_translations("none", "tgt", "ns") == []


def test_lrm_global_manager_singleton(lrm_module):
    m1 = lrm_module.get_resource_manager()
    m2 = lrm_module.get_resource_manager()
    assert m1 is m2


# ---------------------------------------------------------------------------
# core.memory_monitor
# ---------------------------------------------------------------------------
@pytest.fixture
def mm_module(monkeypatch):
    import core.memory_monitor as mm

    monkeypatch.setattr(mm, "HAS_RESOURCE", False)
    monkeypatch.setattr(mm, "HAS_PSUTIL", False)
    monkeypatch.setattr(mm, "resource", None)

    fake_tracemalloc = MagicMock()
    fake_tracemalloc.start = MagicMock()
    fake_tracemalloc.stop = MagicMock()
    fake_tracemalloc.get_traced_memory = MagicMock(return_value=(1048576, 2097152))
    snap = MagicMock()
    stat = types.SimpleNamespace(
        traceback=[types.SimpleNamespace(filename="f.py", lineno=10)],
        size_diff=20000000,
        size=10000000,
    )
    snap.compare_to = MagicMock(return_value=[stat])
    fake_tracemalloc.take_snapshot = MagicMock(return_value=snap)
    monkeypatch.setattr(mm, "tracemalloc", fake_tracemalloc)
    return mm


def test_mm_enable_disable_tracemalloc(mm_module):
    monitor = mm_module.MemoryMonitor()
    monitor.enable_tracemalloc()
    assert monitor._enable_tracemalloc is True
    mm_module.tracemalloc.start.assert_called_once()

    monitor.disable_tracemalloc()
    assert monitor._enable_tracemalloc is False
    mm_module.tracemalloc.stop.assert_called_once()


def test_mm_get_memory_usage_resource_branch(mm_module, monkeypatch):
    monkeypatch.setattr(mm_module, "HAS_RESOURCE", True)
    resource_mock = MagicMock()
    resource_mock.RUSAGE_SELF = 0
    resource_mock.getrusage = MagicMock(return_value=types.SimpleNamespace(ru_maxrss=2048))
    monkeypatch.setattr(mm_module, "resource", resource_mock)

    monitor = mm_module.MemoryMonitor(max_memory_mb=1024)
    info = monitor.get_memory_usage()
    assert info["usage_mb"] == 2.0
    assert info["usage_rate"] == pytest.approx(2.0 / 1024)
    resource_mock.getrusage.assert_called_once()


def test_mm_get_memory_usage_psutil_branch(mm_module, monkeypatch):
    monkeypatch.setattr(mm_module, "HAS_RESOURCE", False)
    monkeypatch.setattr(mm_module, "HAS_PSUTIL", True)
    fake_psutil = types.SimpleNamespace(
        Process=lambda: types.SimpleNamespace(
            memory_info=lambda: types.SimpleNamespace(rss=4194304)
        )
    )
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    monitor = mm_module.MemoryMonitor(max_memory_mb=1024)
    info = monitor.get_memory_usage()
    assert info["usage_mb"] == 4.0
    assert info["usage_rate"] == pytest.approx(4.0 / 1024)


def test_mm_get_memory_usage_fallback_zero(mm_module):
    mm_module.HAS_RESOURCE = False
    mm_module.HAS_PSUTIL = False
    monitor = mm_module.MemoryMonitor()
    info = monitor.get_memory_usage()
    assert info["usage_mb"] == 0
    assert not info["tracemalloc"]


def test_mm_get_memory_usage_tracemalloc(mm_module):
    monitor = mm_module.MemoryMonitor()
    monitor.enable_tracemalloc()
    info = monitor.get_memory_usage()
    assert info["usage_mb"] == 1.0
    assert info["tracemalloc"]["current_traced"] == 1.0
    assert info["tracemalloc"]["peak_traced"] == 2.0


def test_mm_check_memory_usage_states(mm_module, monkeypatch):
    monitor = mm_module.MemoryMonitor(max_memory_mb=100, warning_threshold=0.5)

    monkeypatch.setattr(
        monitor,
        "get_memory_usage",
        lambda: {
            "usage_mb": 10,
            "usage_rate": 0.1,
            "timestamp": "2024-01-01T00:00:00+00:00",
        },
    )
    healthy = monitor.check_memory_usage()
    assert healthy["status"] == "healthy"
    assert "memory_info" in healthy

    monkeypatch.setattr(
        monitor,
        "get_memory_usage",
        lambda: {
            "usage_mb": 60,
            "usage_rate": 0.6,
            "timestamp": "2024-01-01T00:00:00+00:00",
        },
    )
    warning = monitor.check_memory_usage()
    assert warning["status"] == "warning"
    assert "exceeds" in warning["message"]

    monkeypatch.setattr(monitor, "warning_threshold", 0.99)
    monkeypatch.setattr(
        monitor,
        "get_memory_usage",
        lambda: {
            "usage_mb": 97,
            "usage_rate": 0.97,
            "timestamp": "2024-01-01T00:00:00+00:00",
        },
    )
    critical = monitor.check_memory_usage()
    assert critical["status"] == "critical"
    assert "immediate action" in critical["message"]


def test_mm_get_memory_history(mm_module):
    monitor = mm_module.MemoryMonitor()
    monitor._memory_history = [
        {"usage_mb": 1, "usage_rate": 0.1, "timestamp": "t1"},
        {"usage_mb": 2, "usage_rate": 0.2, "timestamp": "t2"},
    ]
    assert len(monitor.get_memory_history(1)) == 1
    assert monitor.get_memory_history(1)[0]["usage_mb"] == 2


def test_mm_get_memory_leak_candidates(mm_module):
    monitor = mm_module.MemoryMonitor()
    assert monitor.get_memory_leak_candidates() == []

    monitor._enable_tracemalloc = True
    candidates = monitor.get_memory_leak_candidates()
    assert len(candidates) == 1
    assert candidates[0]["file"] == "f.py"
    assert candidates[0]["line"] == 10


@pytest.mark.asyncio
async def test_mm_memory_monitor_decorator(mm_module):
    @mm_module.memory_monitor_decorator(max_memory_mb=64)
    async def work(x):
        return x * 2

    assert await work(5) == 10


@pytest.mark.asyncio
async def test_mm_memory_monitor_decorator_exception(mm_module):
    @mm_module.memory_monitor_decorator(max_memory_mb=64)
    async def boom():
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        await boom()


def test_mm_leak_detector(mm_module):
    detector = mm_module.MemoryLeakDetector()
    assert detector.take_snapshot("x") is None
    assert detector.compare_snapshots("a", "b") == []
    assert detector.detect_leaks() == []

    detector.enable()
    assert detector._enable_tracemalloc is True
    detector.take_snapshot("s1")
    detector.take_snapshot("s2")
    stats = detector.compare_snapshots("s1", "s2")
    assert len(stats) == 1
    assert detector.compare_snapshots("missing1", "s2") == []

    leaks = detector.detect_leaks(threshold_mb=1)
    assert len(leaks) == 1
    detector.disable()
    assert detector._enable_tracemalloc is False


@pytest.mark.asyncio
async def test_mm_setup_memory_monitoring(mm_module, monkeypatch):
    fresh_monitor = mm_module.MemoryMonitor()
    fresh_detector = mm_module.MemoryLeakDetector()
    monkeypatch.setattr(mm_module, "memory_monitor", fresh_monitor)
    monkeypatch.setattr(mm_module, "memory_leak_detector", fresh_detector)

    result = await mm_module.setup_memory_monitoring()
    assert result["status"] == "success"
    assert result["tracemalloc_enabled"] is True
    assert result["leak_detection_enabled"] is True
    assert result["max_memory_mb"] == 1024


def test_mm_global_instances(mm_module):
    assert isinstance(mm_module.memory_monitor, mm_module.MemoryMonitor)
    assert isinstance(mm_module.memory_leak_detector, mm_module.MemoryLeakDetector)
