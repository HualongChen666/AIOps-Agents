# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.performance_regression_detector,
core.performance_data_collector, core.anomaly_engine, core.qdrant_service and
core.api_helpers.
"""
import asyncio
import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request

import core.anomaly_engine as anomaly_engine
import core.api_helpers as api_helpers
import core.performance_data_collector as performance_data_collector
import core.performance_regression_detector as performance_regression_detector
import core.qdrant_service as qdrant_service

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _make_async_session(result_objects=None, raise_on=None, raise_on_commit=False):
    """Build a mock AsyncSession suitable for the async DB modules."""
    if result_objects is None:
        result_objects = []

    result = MagicMock()
    result.scalar_one_or_none = MagicMock(
        return_value=result_objects[0] if result_objects else None
    )
    result.scalars = MagicMock(
        return_value=MagicMock(all=MagicMock(return_value=result_objects))
    )

    if raise_on:
        session_execute = AsyncMock(side_effect=raise_on)
    else:
        session_execute = AsyncMock(return_value=result)

    async def refresh(obj):
        if not getattr(obj, "id", None):
            obj.id = 1

    async def close():
        return None

    def add(obj):
        if not getattr(obj, "id", None):
            obj.id = 1

    def add_all(objects):
        for i, obj in enumerate(objects, start=1):
            if not getattr(obj, "id", None):
                obj.id = i

    session = MagicMock()
    session.execute = session_execute
    session.add = MagicMock(side_effect=add)
    session.add_all = MagicMock(side_effect=add_all)
    session.refresh = AsyncMock(side_effect=refresh)
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed")) if raise_on_commit else AsyncMock()
    session.close = AsyncMock(side_effect=close)
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)

    return session


# -----------------------------------------------------------------------------
# core.performance_regression_detector
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_baseline():
    b = MagicMock()
    b.component = "api-gateway"
    b.environment = "dev"
    b.is_active = True
    b.operation = "GET /orders"
    b.target_p95_ms = 100.0
    b.target_p99_ms = 150.0
    b.target_throughput = 500.0
    b.regression_threshold = 0.1
    b.critical_threshold = 0.3
    return b


@pytest.mark.asyncio
async def test_regression_detector_context_manager(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    async with detector as d:
        assert d is detector
        assert d.session is not None
    assert session.close.called


@pytest.mark.asyncio
async def test_detect_regression_no_baseline(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("missing", 200.0)
    assert result is None


@pytest.mark.asyncio
async def test_detect_regression_p95_warning(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("api-gateway", 120.0)
    assert result is not None
    assert result["severity"] == "warning"
    assert result["deviation"] == pytest.approx(0.2)


@pytest.mark.asyncio
async def test_detect_regression_p95_critical(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("api-gateway", 160.0)
    assert result["severity"] == "critical"
    assert result["deviation"] == pytest.approx(0.6)


@pytest.mark.asyncio
async def test_detect_regression_p99(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression(
        "api-gateway", 200.0, metric_name="p99_time_ms"
    )
    assert result is not None
    assert result["baseline_value"] == 150.0


@pytest.mark.asyncio
async def test_detect_regression_throughput(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression(
        "api-gateway", 600.0, metric_name="throughput"
    )
    assert result is not None
    assert result["baseline_value"] == 500.0


@pytest.mark.asyncio
async def test_detect_regression_unsupported_metric(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression(
        "api-gateway", 10.0, metric_name="unknown"
    )
    assert result is None


@pytest.mark.asyncio
async def test_detect_regression_baseline_none_metric(monkeypatch, mock_baseline):
    mock_baseline.target_p99_ms = None
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression(
        "api-gateway", 10.0, metric_name="p99_time_ms"
    )
    assert result is None


@pytest.mark.asyncio
async def test_detect_regression_no_deviation(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("api-gateway", 100.0)
    assert result is None


@pytest.mark.asyncio
async def test_detect_regression_zero_baseline(monkeypatch):
    b = MagicMock()
    b.target_p95_ms = 0.0
    b.regression_threshold = 0.1
    b.critical_threshold = 0.3
    b.operation = "GET /"
    b.environment = "dev"
    session = _make_async_session([b])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("api-zero", 50.0)
    assert result is None


@pytest.mark.asyncio
async def test_detect_regression_exception(monkeypatch):
    session = _make_async_session(raise_on=RuntimeError("boom"))
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    result = await detector.detect_regression("api", 100.0)
    assert result is None


@pytest.mark.asyncio
async def test_batch_detect_regressions(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    metrics_data = [
        {"component": "api-gateway", "p95_time_ms": 80.0},
        {"component": "api-gateway", "p95_time_ms": 130.0},
        {"component": "unknown", "p95_time_ms": None},
    ]
    results = await detector.batch_detect_regressions(metrics_data)
    assert len(results) == 2
    assert all(r["severity"] == "warning" for r in results)


@pytest.mark.asyncio
async def test_get_active_regressions(monkeypatch):
    r1 = MagicMock()
    r1.regression_id = "reg-1"
    r1.component = "api"
    r1.operation = "GET"
    r1.baseline_value = 100.0
    r1.current_value = 120.0
    r1.deviation = 0.2
    r1.severity = "warning"
    r1.detected_at = datetime.datetime.now()
    r1.status = "open"
    r1.environment = "dev"

    session = _make_async_session([r1])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    results = await detector.get_active_regressions(environment="dev", severity="warning")
    assert len(results) == 1
    assert results[0]["regression_id"] == "reg-1"


@pytest.mark.asyncio
async def test_get_active_regressions_exception(monkeypatch):
    session = _make_async_session(raise_on=RuntimeError("boom"))
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    results = await detector.get_active_regressions()
    assert results == []


@pytest.mark.asyncio
async def test_acknowledge_regression_found(monkeypatch):
    reg = MagicMock()
    reg.status = "open"
    session = _make_async_session([reg])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    assert await detector.acknowledge_regression("reg-1", "admin") is True
    assert reg.status == "acknowledged"
    assert reg.acknowledged_by == "admin"
    assert reg.acknowledged_at is not None


@pytest.mark.asyncio
async def test_acknowledge_regression_not_found(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    assert await detector.acknowledge_regression("reg-1", "admin") is False


@pytest.mark.asyncio
async def test_resolve_regression_found(monkeypatch):
    reg = MagicMock()
    reg.status = "open"
    session = _make_async_session([reg])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    assert await detector.resolve_regression("reg-1") is True
    assert reg.status == "resolved"
    assert reg.resolved_at is not None


@pytest.mark.asyncio
async def test_resolve_regression_not_found(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    detector = performance_regression_detector.PerformanceRegressionDetector()
    assert await detector.resolve_regression("reg-1") is False


@pytest.mark.asyncio
async def test_check_performance_regression(monkeypatch, mock_baseline):
    session = _make_async_session([mock_baseline])
    monkeypatch.setattr(
        performance_regression_detector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    result = await performance_regression_detector.check_performance_regression(
        "api-gateway", 130.0, environment="dev"
    )
    assert result is not None
    assert result["severity"] == "warning"


# -----------------------------------------------------------------------------
# core.performance_data_collector
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_metric_row():
    m = MagicMock()
    m.id = 42
    m.test_id = "t-1"
    m.test_name = "load-test"
    m.test_type = "api"
    m.component = "api"
    m.operation = "GET"
    m.mean_time_ms = 50.0
    m.min_time_ms = 10.0
    m.max_time_ms = 100.0
    m.p50_time_ms = 50.0
    m.p95_time_ms = 100.0
    m.p99_time_ms = 150.0
    m.std_dev_ms = 5.0
    m.throughput_ops = 100.0
    m.error_rate = 0.01
    m.total_requests = 10
    m.timestamp = datetime.datetime.now()
    return m


@pytest.mark.asyncio
async def test_data_collector_context_manager():
    collector = performance_data_collector.PerformanceDataCollector()
    async with collector as c:
        assert c is collector


@pytest.mark.asyncio
async def test_collect_metric(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    record_id = await collector.collect_metric(
        {
            "test_id": "t-1",
            "test_name": "load",
            "test_type": "api",
            "component": "api",
            "operation": "GET",
            "mean_time_ms": 50.0,
            "min_time_ms": 10.0,
            "max_time_ms": 100.0,
            "environment": "dev",
        }
    )
    assert record_id == "1"


@pytest.mark.asyncio
async def test_collect_metric_exception(monkeypatch):
    session = _make_async_session(raise_on_commit=True)
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    with pytest.raises(RuntimeError):
        await collector.collect_metric({"test_id": "t-1", "test_name": "x", "test_type": "api", "component": "api", "operation": "GET"})


@pytest.mark.asyncio
async def test_collect_batch_metrics(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    ids = await collector.collect_batch_metrics(
        [
            {"test_id": "t-1", "test_name": "a", "test_type": "api", "component": "api", "operation": "GET"},
            {"test_id": "t-2", "test_name": "b", "test_type": "api", "component": "api", "operation": "POST"},
        ]
    )
    assert len(ids) == 2
    assert ids[0] == "1"
    assert ids[1] == "2"


@pytest.mark.asyncio
async def test_query_metrics_all_filters(monkeypatch, mock_metric_row):
    session = _make_async_session([mock_metric_row])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    start = datetime.datetime.now() - datetime.timedelta(hours=1)
    end = datetime.datetime.now()
    results = await collector.query_metrics(
        component="api",
        test_type="api",
        environment="dev",
        start_time=start,
        end_time=end,
        limit=10,
    )
    assert len(results) == 1
    assert results[0]["component"] == "api"


@pytest.mark.asyncio
async def test_get_aggregated_metrics_hour(monkeypatch, mock_metric_row):
    session = _make_async_session([mock_metric_row])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    results = await collector.get_aggregated_metrics(
        "api", "p95_time_ms", interval="hour", hours=24
    )
    assert isinstance(results, list)
    assert results[0]["count"] == 1


@pytest.mark.asyncio
async def test_get_aggregated_metrics_day(monkeypatch, mock_metric_row):
    session = _make_async_session([mock_metric_row])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    collector = performance_data_collector.PerformanceDataCollector()
    results = await collector.get_aggregated_metrics(
        "api", "p95_time_ms", interval="day", hours=24
    )
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_collect_performance_test_result(monkeypatch):
    session = _make_async_session([])
    monkeypatch.setattr(
        performance_data_collector, "AsyncSessionLocal", MagicMock(return_value=session)
    )
    record_id = await performance_data_collector.collect_performance_test_result(
        {"test_id": "t-1", "test_name": "x", "test_type": "api", "component": "api", "operation": "GET"}
    )
    assert record_id == "1"


# -----------------------------------------------------------------------------
# core.anomaly_engine
# -----------------------------------------------------------------------------
def test_make_timestamp():
    now = datetime.datetime.now()
    assert anomaly_engine._make_timestamp(now) == now.isoformat()
    assert anomaly_engine._make_timestamp("12:34:56").startswith(datetime.date.today().isoformat())
    assert anomaly_engine._make_timestamp("2025-01-01T00:00:00") == "2025-01-01T00:00:00"
    assert "T" in anomaly_engine._make_timestamp(None)


def test_detect_anomalies_non_list():
    assert anomaly_engine.detect_anomalies({}, "cpu") == []


def test_detect_anomalies_too_few():
    assert anomaly_engine.detect_anomalies({"cpu": [1.0, 2.0]}, "cpu") == []


def test_detect_anomalies_no_anomaly():
    history = {
        "cpu": [10.0, 10.1, 10.0, 10.1, 10.0],
        "timestamps": ["00:00:00"] * 5,
    }
    assert anomaly_engine.detect_anomalies(history, "cpu") == []


def test_detect_anomalies_high_cpu():
    history = {
        "cpu": [10.0] * 29 + [95.0],
        "timestamps": [f"00:{i:02d}:00" for i in range(30)],
    }
    result = anomaly_engine.detect_anomalies(history, "cpu")
    assert len(result) == 1
    assert result[0]["metric"] == "CPU使用率"
    assert result[0]["confidence"] > 0


def test_detect_anomalies_low_memory():
    history = {
        "memory": [50.0] * 29 + [5.0],
        "timestamps": [f"00:{i:02d}:00" for i in range(30)],
    }
    result = anomaly_engine.detect_anomalies(history, "memory")
    assert len(result) == 1
    assert result[0]["metric"] == "内存使用率"


def test_detect_anomalies_net_in():
    history = {
        "net_in": [1000.0] * 29 + [50000.0],
        "timestamps": [f"00:{i:02d}:00" for i in range(30)],
    }
    result = anomaly_engine.detect_anomalies(history, "net_in")
    assert len(result) == 1
    assert result[0]["metric"] == "网络入流量"


def test_detect_anomalies_unknown_metric():
    history = {"disk": [10.0] * 29 + [95.0]}
    result = anomaly_engine.detect_anomalies(history, "disk", threshold_z=1.5)
    assert result[0]["metric"] == "disk"


def test_detect_anomalies_zero_stdev():
    history = {"cpu": [10.0] * 30}
    assert anomaly_engine.detect_anomalies(history, "cpu") == []


def test_detect_anomalies_invalid_values():
    history = {"cpu": ["bad", 1.0, 2.0]}
    assert anomaly_engine.detect_anomalies(history, "cpu") == []


def test_detect_all_anomalies():
    history = {
        "cpu": [10.0] * 29 + [95.0],
        "memory": [50.0] * 29 + [5.0],
        "net_in": [1000.0] * 29 + [50000.0],
        "timestamps": [f"00:{i:02d}:00" for i in range(30)],
    }
    results = anomaly_engine.detect_all_anomalies(history)
    assert len(results) == 3
    assert all(isinstance(r, dict) for r in results)


# -----------------------------------------------------------------------------
# core.qdrant_service
# -----------------------------------------------------------------------------
@pytest.fixture
def qdrant_mocks(monkeypatch):
    """Enable Qdrant availability and mock qdrant_client models/classes."""
    monkeypatch.setattr(qdrant_service, "QDRANT_AVAILABLE", True)
    qdrant_service._qdrant_client = None

    mock_client_class = MagicMock()
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    monkeypatch.setattr(qdrant_service, "QdrantClient", mock_client_class)

    monkeypatch.setattr(qdrant_service, "Distance", MagicMock())
    qdrant_service.Distance.COSINE = "Cosine"
    qdrant_service.Distance.EUCLID = "Euclid"
    qdrant_service.Distance.DOT = "Dot"

    monkeypatch.setattr(qdrant_service, "PointStruct", MagicMock())
    monkeypatch.setattr(qdrant_service, "VectorParams", MagicMock())
    monkeypatch.setattr(qdrant_service, "FieldCondition", MagicMock())
    monkeypatch.setattr(qdrant_service, "MatchValue", MagicMock())
    monkeypatch.setattr(qdrant_service, "Filter", MagicMock())

    # Patch the real qdrant_client.models namespace so the dynamic
    # import inside qdrant_service.search resolves to our mocks.
    try:
        import qdrant_client.models as _qdrant_models
        monkeypatch.setattr(_qdrant_models, "Filter", qdrant_service.Filter)
        monkeypatch.setattr(_qdrant_models, "PointStruct", qdrant_service.PointStruct)
        monkeypatch.setattr(_qdrant_models, "VectorParams", qdrant_service.VectorParams)
        monkeypatch.setattr(_qdrant_models, "FieldCondition", qdrant_service.FieldCondition)
        monkeypatch.setattr(_qdrant_models, "MatchValue", qdrant_service.MatchValue)
    except ImportError:
        pass

    return mock_client_class, mock_client


def test_get_qdrant_client_unavailable(monkeypatch):
    monkeypatch.setattr(qdrant_service, "QDRANT_AVAILABLE", False)
    qdrant_service._qdrant_client = None
    assert qdrant_service.get_qdrant_client() is None


def test_get_qdrant_client_disabled(monkeypatch, qdrant_mocks):
    monkeypatch.setenv("QDRANT_DISABLED", "true")
    qdrant_service._qdrant_client = None
    assert qdrant_service.get_qdrant_client() is None


def test_get_qdrant_client_initialization_error(monkeypatch, qdrant_mocks):
    mock_client_class, _ = qdrant_mocks
    mock_client_class.side_effect = RuntimeError("qdrant down")
    qdrant_service._qdrant_client = None
    assert qdrant_service.get_qdrant_client() is None


def test_get_qdrant_client_caches(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = None
    c1 = qdrant_service.get_qdrant_client()
    c2 = qdrant_service.get_qdrant_client()
    assert c1 is c2 is mock_client


def test_list_collections_success(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_collection = MagicMock()
    mock_collection.name = "incidents"
    mock_client.get_collections.return_value = MagicMock(collections=[mock_collection])
    qdrant_service._qdrant_client = mock_client
    assert qdrant_service.list_collections() == ["incidents"]


def test_list_collections_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.get_collections.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    assert qdrant_service.list_collections() == []


def test_create_collection_success(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    result = qdrant_service.create_collection("incidents", 384, distance="Cosine")
    assert result["status"] == "success"
    assert mock_client.create_collection.called


def test_create_collection_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.create_collection.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    with pytest.raises(RuntimeError):
        qdrant_service.create_collection("incidents", 384)


def test_delete_collection_success(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    result = qdrant_service.delete_collection("incidents")
    assert result["status"] == "success"


def test_delete_collection_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.delete_collection.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    with pytest.raises(RuntimeError):
        qdrant_service.delete_collection("incidents")


def test_upsert_points_success(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    points = [
        {"id": "p1", "vector": [0.1, 0.2], "payload": {"tag": "x"}},
        {"id": "p2", "vector": [0.3, 0.4]},
    ]
    result = qdrant_service.upsert_points("incidents", points)
    assert result["status"] == "success"
    assert result["count"] == 2


def test_upsert_points_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.upsert.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    with pytest.raises(RuntimeError):
        qdrant_service.upsert_points("incidents", [{"id": "p1", "vector": [0.1]}])


def test_search_with_filter(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    mock_result = MagicMock()
    mock_result.id = "p1"
    mock_result.score = 0.95
    mock_result.payload = {"x": "y"}
    mock_client.search.return_value = [mock_result]

    results = qdrant_service.search(
        "incidents", [0.1, 0.2], top_k=3, filter={"tag": "x"}
    )
    assert len(results) == 1
    assert results[0]["id"] == "p1"


def test_search_without_filter(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    mock_client.search.return_value = []
    results = qdrant_service.search("incidents", [0.1, 0.2])
    assert results == []


def test_search_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.search.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    with pytest.raises(RuntimeError):
        qdrant_service.search("incidents", [0.1])


def test_delete_points_success(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    result = qdrant_service.delete_points("incidents", ["p1", "p2"])
    assert result["count"] == 2


def test_delete_points_failure(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.delete.side_effect = RuntimeError("fail")
    qdrant_service._qdrant_client = mock_client
    with pytest.raises(RuntimeError):
        qdrant_service.delete_points("incidents", ["p1"])


def test_health_check_unavailable(monkeypatch):
    monkeypatch.setattr(qdrant_service, "QDRANT_AVAILABLE", False)
    qdrant_service._qdrant_client = None
    assert qdrant_service.health_check()["status"] == "unavailable"


def test_health_check_healthy(qdrant_mocks):
    _, mock_client = qdrant_mocks
    qdrant_service._qdrant_client = mock_client
    assert qdrant_service.health_check()["status"] == "healthy"


def test_health_check_unhealthy(qdrant_mocks):
    _, mock_client = qdrant_mocks
    mock_client.get_collections.side_effect = RuntimeError("timeout")
    qdrant_service._qdrant_client = mock_client
    assert qdrant_service.health_check()["status"] == "unhealthy"


# -----------------------------------------------------------------------------
# core.api_helpers
# -----------------------------------------------------------------------------
def test_handle_api_error():
    with pytest.raises(HTTPException) as exc:
        api_helpers.handle_api_error(
            "日志采集", ValueError("disk full"), status_code=503, detail_prefix="采集"
        )
    assert exc.value.status_code == 503
    assert "disk full" in exc.value.detail


def test_handle_api_error_with_context():
    with pytest.raises(HTTPException) as exc:
        api_helpers.handle_api_error(
            "通知发送",
            ValueError("timeout"),
            log_context={"host": "h1"},
            max_detail_length=20,
        )
    assert exc.value.status_code == 500
    assert len(exc.value.detail) <= 20


def test_validate_required_fields_ok():
    api_helpers.validate_required_fields(
        {"level": "critical", "title": "x", "desc": "y"},
        ["level", "title", "desc"],
    )


def test_validate_required_fields_not_dict():
    with pytest.raises(HTTPException) as exc:
        api_helpers.validate_required_fields("bad", ["x"])
    assert exc.value.status_code == 422


def test_validate_required_fields_missing():
    with pytest.raises(HTTPException) as exc:
        api_helpers.validate_required_fields({"level": "", "title": "x"}, ["level", "desc"])
    assert "desc" in exc.value.detail


def test_log_operation_start(caplog):
    with caplog.at_level("INFO", logger="core.api_helpers"):
        api_helpers.log_operation_start("备份", host="s1")
        assert "备份开始" in caplog.text


def test_log_operation_success(caplog):
    with caplog.at_level("INFO", logger="core.api_helpers"):
        api_helpers.log_operation_success("备份")
        assert "备份成功" in caplog.text


def test_create_success_response():
    resp = api_helpers.create_success_response([1, 2], message="ok", total=2)
    assert resp["status"] == "ok"
    assert resp["message"] == "ok"
    assert resp["data"] == [1, 2]
    assert resp["total"] == 2


def test_create_success_response_no_data():
    resp = api_helpers.create_success_response(None)
    assert "data" not in resp


def test_create_error_response():
    resp = api_helpers.create_error_response("bad", 400, error_code="E1", field="x")
    assert resp["status"] == "error"
    assert resp["error_code"] == "E1"
    assert resp["field"] == "x"


def test_with_error_handling_async_success():
    @api_helpers.with_error_handling("测试")
    async def async_add(a, b):
        return a + b

    assert asyncio.run(async_add(1, b=2)) == 3


def test_with_error_handling_async_http_exception_passthrough():
    @api_helpers.with_error_handling("测试")
    async def async_raise():
        raise HTTPException(status_code=418)

    with pytest.raises(HTTPException):
        asyncio.run(async_raise())


def test_with_error_handling_async_other_exception():
    @api_helpers.with_error_handling("测试", status_code=400)
    async def async_fail():
        raise ValueError("boom")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(async_fail())
    assert exc.value.status_code == 400


def test_with_error_handling_sync_success():
    @api_helpers.with_error_handling("测试")
    def sync_mul(a, b):
        return a * b

    assert sync_mul(2, 3) == 6


def test_with_error_handling_sync_error():
    @api_helpers.with_error_handling("测试")
    def sync_fail():
        raise RuntimeError("boom")

    with pytest.raises(HTTPException) as exc:
        sync_fail()
    assert exc.value.status_code == 500


def test_find_host_config():
    hosts = [
        {"name": "s1", "host": "10.0.0.1"},
        {"name": "s2", "host": "10.0.0.2"},
    ]
    assert api_helpers.find_host_config("s1", hosts)["host"] == "10.0.0.1"
    assert api_helpers.find_host_config("10.0.0.2", hosts)["name"] == "s2"
    assert api_helpers.find_host_config("", hosts) is None
    assert api_helpers.find_host_config("bad host!", hosts) is None
    assert api_helpers.find_host_config(None, hosts) is None


def test_validate_hostname():
    assert api_helpers.validate_hostname("  server-01_2.local:8080  ") == "server-01_2.local:8080"


def test_validate_hostname_invalid():
    with pytest.raises(ValueError) as exc:
        api_helpers.validate_hostname("host with space")
    assert "host_name" in str(exc.value)

    with pytest.raises(ValueError):
        api_helpers.validate_hostname("")

    with pytest.raises(ValueError):
        api_helpers.validate_hostname(None)


def test_get_operator_ip():
    request = MagicMock(spec=Request)
    request.client = MagicMock()
    request.client.host = "192.168.1.1"
    assert api_helpers.get_operator_ip(request) == "192.168.1.1"

    request.client = None
    assert api_helpers.get_operator_ip(request) == "unknown"


def test_hostname_field_validator():
    assert api_helpers.hostname_field_validator("  host_1  ") == "host_1"
    with pytest.raises(ValueError):
        api_helpers.hostname_field_validator("bad!")
