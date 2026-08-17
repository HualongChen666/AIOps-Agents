# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.call_chain_search,
core.api_response_standard, core.plugin_marketplace,
core.performance_optimizer and core.concurrency_control.
"""

import asyncio  # noqa: F401  # Imported for test setup
import importlib
import json  # noqa: F401  # Imported for test setup
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

import core.api_response_standard as api_resp
import core.call_chain_search as ccs
import core.concurrency_control as cc
import core.plugin_marketplace as pm

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.call_chain_search
# -----------------------------------------------------------------------------


@pytest.fixture
def chain_manager():
    return ccs.get_call_chain_search_manager()


def _sample_trace(
    trace_id, service, operation, status, duration, start, tags=None, metadata=None, **kwargs
):
    data = {
        "trace_id": trace_id,
        "service_name": service,
        "operation_name": operation,
        "status": status,
        "duration_ms": duration,
        "start_time": start.isoformat() if isinstance(start, datetime) else start,
        "end_time": (start + timedelta(milliseconds=duration)).isoformat(),
        "tags": tags or {},
        "metadata": metadata or {},
    }
    data.update(kwargs)
    return data


def test_add_and_search_call_chains(chain_manager):
    t1 = _sample_trace(
        "t1", "svc-a", "op-x", "ok", 120, datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    )
    t2 = _sample_trace(
        "t2", "svc-b", "op-y", "error", 250, datetime(2024, 1, 1, 12, 1, 0, tzinfo=timezone.utc)
    )

    chain_manager.add_call_chain(t1)
    chain_manager.add_call_chain(t2)
    chain_manager.add_call_chain({"service_name": "missing"})  # no trace_id

    assert chain_manager.search_by_trace_id("t1") is t1
    assert chain_manager.search_by_trace_id("missing") is None
    assert len(chain_manager.search_by_service_name("svc-a")) == 1
    assert len(chain_manager.search_by_service_name("svc-b", limit=1)) == 1
    assert len(chain_manager.search_by_service_name("none")) == 0

    stats = chain_manager.get_statistics()
    assert stats["indexed_traces"] == 2
    assert stats["total_searches"] >= 4
    assert stats["indexed_services"] == 2


def test_search_by_criteria_all_paths(chain_manager):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t1 = _sample_trace("t1", "svc-a", "op-x", "ok", 120, start, tags={"env": "prod"}, region="us")
    t2 = _sample_trace(
        "t2", "svc-a", "op-y", "error", 250, start + timedelta(minutes=2), tags={"env": "dev"}
    )
    t3 = _sample_trace(
        "t3", "svc-b", "op-x", "ok", 80, start + timedelta(minutes=5), tags={"env": "prod"}
    )

    for t in (t1, t2, t3):
        chain_manager.add_call_chain(t)

    criteria = ccs.SearchCriteria(
        service_name="svc-a",
        operation_name="op-x",
        status="ok",
        min_duration_ms=100,
        max_duration_ms=300,
        start_time=start,
        end_time=start + timedelta(minutes=10),
        tags={"env": "prod"},
        custom_filters=[
            ccs.SearchFilter(field="region", operator=ccs.SearchOperator.EQUALS, value="us"),
        ],
        limit=10,
        offset=0,
        sort_by="duration_ms",
        sort_order=ccs.SortOrder.DESC,
    )
    results = chain_manager.search_by_criteria(criteria)
    assert len(results) == 1
    assert results[0].trace_id == "t1"
    assert results[0].match_score > 0

    # Sort ascending by start_time
    criteria2 = ccs.SearchCriteria(
        service_name="svc-a",
        sort_by="start_time",
        sort_order=ccs.SortOrder.ASC,
    )
    results2 = chain_manager.search_by_criteria(criteria2)
    assert results2[0].start_time <= results2[-1].start_time

    # Pagination offset
    criteria3 = ccs.SearchCriteria(
        service_name="svc-a",
        limit=1,
        offset=1,
        sort_by="start_time",
        sort_order=ccs.SortOrder.ASC,
    )
    results3 = chain_manager.search_by_criteria(criteria3)
    assert len(results3) == 1


def test_custom_filter_operators(chain_manager):
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    t = _sample_trace(
        "op",
        "svc",
        "op",
        "ok",
        120,
        start,
        count=10,
        name="hello world",
        items=["a", "b"],
    )
    chain_manager.add_call_chain(t)

    def search(field, operator, value):
        criteria = ccs.SearchCriteria(
            custom_filters=[ccs.SearchFilter(field=field, operator=operator, value=value)]
        )
        return {r.trace_id for r in chain_manager.search_by_criteria(criteria)}

    assert "op" in search("count", ccs.SearchOperator.EQUALS, 10)
    assert "op" in search("count", ccs.SearchOperator.NOT_EQUALS, 5)
    assert "op" in search("name", ccs.SearchOperator.CONTAINS, "world")
    assert "op" in search("name", ccs.SearchOperator.NOT_CONTAINS, "nope")
    assert "op" in search("count", ccs.SearchOperator.GREATER_THAN, 5)
    assert "op" in search("count", ccs.SearchOperator.LESS_THAN, 20)
    assert "op" in search("count", ccs.SearchOperator.GREATER_THAN_OR_EQUAL, 10)
    assert "op" in search("count", ccs.SearchOperator.LESS_THAN_OR_EQUAL, 10)
    assert "op" in search("count", ccs.SearchOperator.IN, [10, 20])
    assert "op" in search("count", ccs.SearchOperator.NOT_IN, [5])
    assert "op" in search("name", ccs.SearchOperator.REGEX, "hello.*")

    # Unknown operator falls into the else branch and matches everything
    class _FakeOp:
        pass

    assert "op" in search("count", _FakeOp(), 1)

    # Type/value errors return False
    assert "op" not in search("count", ccs.SearchOperator.GREATER_THAN, "not-a-number")
    assert "op" not in search("count", ccs.SearchOperator.IN, "a")


def test_parse_datetime_and_missing_fields(chain_manager):
    # Invalid start_time format is handled by _parse_datetime
    assert chain_manager._parse_datetime("not-a-date") is None
    assert chain_manager._parse_datetime(datetime.now(timezone.utc)) is not None

    # add_call_chain silently drops entries without a trace_id
    chain_manager.add_call_chain({"service_name": "svc"})
    assert chain_manager.search_by_trace_id("missing") is None

    # start_time as datetime object directly
    chain_manager.add_call_chain(
        {
            "trace_id": "dt",
            "service_name": "svc",
            "operation_name": "op",
            "status": "ok",
            "duration_ms": 100,
            "start_time": datetime.now(timezone.utc),
        }
    )
    assert chain_manager.search_by_trace_id("dt") is not None


# -----------------------------------------------------------------------------
# core.api_response_standard
# -----------------------------------------------------------------------------


def test_api_response_dicts():
    ok = api_resp.create_success_response({"id": 1}, message="Created")
    assert ok["success"] is True
    assert ok["data"]["id"] == 1
    assert ok["message"] == "Created"

    err = api_resp.create_error_response("boom", api_resp.ErrorCode.INTERNAL_ERROR, "message-boom")
    assert err["success"] is False
    assert err["error"] == "boom"
    assert err["error_code"] == api_resp.ErrorCode.INTERNAL_ERROR
    assert err["message"] == "message-boom"

    response = api_resp.APIResponse(success=False, error="x", error_code="E", message="m")
    d = response.to_dict()
    assert d["success"] is False
    assert "data" not in d
    assert d["message"] == "m"


def test_pagination_and_paginated_response():
    params = api_resp.PaginationParams(page=2, size=10, max_size=50)
    assert params.offset == 10
    assert params.limit == 10

    with pytest.raises(ValueError, match="Page must be >= 1"):
        api_resp.PaginationParams(page=0)
    with pytest.raises(ValueError, match="Size must be >= 1"):
        api_resp.PaginationParams(size=0)
    with pytest.raises(ValueError, match="Size must be <= 100"):
        api_resp.PaginationParams(page=1, size=101, max_size=100)

    paged = api_resp.create_paginated_response([{"id": 1}], total=1, page=1, size=20)
    assert paged["data"]["total"] == 1
    assert paged["data"]["has_next"] is False
    assert paged["data"]["has_prev"] is False

    paged2 = api_resp.PaginatedResponse([], total=0, page=1, size=20).to_dict()
    assert paged2["data"]["total_pages"] == 0


def test_api_response_middleware_wraps_json():
    async def app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"hello": "world"}).encode(),
                "more_body": False,
            }
        )

    middleware = api_resp.APIResponseMiddleware(app)
    scope = {"type": "http"}
    received = []

    async def _send(message):
        received.append(message)

    asyncio.run(middleware(scope, None, _send))

    assert received[0]["type"] == "http.response.start"
    body = json.loads(received[1]["body"].decode())
    assert body["success"] is True
    assert body["data"] == {"hello": "world"}


def test_api_response_middleware_error_and_non_json():
    async def error_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 422,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": json.dumps({"detail": "invalid"}).encode(),
                "more_body": False,
            }
        )

    received = []

    async def _send(message):
        received.append(message)

    middleware = api_resp.APIResponseMiddleware(error_app)
    asyncio.run(middleware({"type": "http"}, None, _send))
    body = json.loads(received[1]["body"].decode())
    assert body["success"] is False
    assert body["error_code"] == "HTTP 422"

    # Non-json content type is passed through unchanged
    async def plain_app(scope, receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/plain")],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"ok",
                "more_body": False,
            }
        )

    received2 = []

    async def _send2(message):
        received2.append(message)

    middleware2 = api_resp.APIResponseMiddleware(plain_app)
    asyncio.run(middleware2({"type": "http"}, None, _send2))
    assert received2[1]["body"] == b"ok"

    # Non-http scope passes through
    async def passthrough(scope, receive, send):
        await send({"type": "lifespan.startup.complete"})

    received3 = []

    async def _send3(message):
        received3.append(message)

    middleware3 = api_resp.APIResponseMiddleware(passthrough)
    asyncio.run(middleware3({"type": "lifespan"}, None, _send3))
    assert received3[0]["type"] == "lifespan.startup.complete"


def test_api_response_middleware_already_wrapped():
    async def app(scope, receive, send):
        payload = json.dumps({"code": 0, "data": []}).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": payload, "more_body": False})

    received = []

    async def _send(message):
        received.append(message)

    middleware = api_resp.APIResponseMiddleware(app)
    asyncio.run(middleware({"type": "http"}, None, _send))
    body = json.loads(received[1]["body"].decode())
    assert "code" in body
    assert "data" in body


def test_create_http_exception():
    exc = api_resp.create_http_exception(404, api_resp.ErrorCode.RESOURCE_NOT_FOUND, "missing")
    assert exc.status_code == 404
    assert exc.detail["success"] is False
    assert exc.detail["error_code"] == api_resp.ErrorCode.RESOURCE_NOT_FOUND


# -----------------------------------------------------------------------------
# core.plugin_marketplace
# -----------------------------------------------------------------------------


@pytest.fixture
def marketplace():
    storage = MagicMock()
    storage.load.return_value = {}
    storage.save.return_value = None
    return pm.create_plugin_marketplace(
        storage=storage,
        config={
            "private_key": "secret-key",
            "public_key": "public-key",
            "signature_algorithm": "SHA256",
        },
    )


def _package(data: bytes = b"package-data"):
    return data


def test_plugin_registration_and_security_levels(marketplace):
    p1 = marketplace.register_plugin(
        name="log-viewer",
        version="1.0.0",
        description="View logs",
        author="alice",
        download_url="https://example.com/log-viewer-1.0.0.zip",
        package_data=_package(),
        dependencies=["base-plugin"],
        metadata={"requires_network": True},
    )
    assert p1.security_level == pm.SecurityLevel.HIGH
    assert p1.signature is not None
    assert p1.signature.verified is True

    p2 = marketplace.register_plugin(
        name="privileged-tool",
        version="0.1.0",
        description="Root tool",
        author="bob",
        download_url="https://example.com/p.zip",
        package_data=b"different",
        metadata={"requires_privileged": True},
    )
    assert p2.security_level == pm.SecurityLevel.CRITICAL

    p3 = marketplace.register_plugin(
        name="simple",
        version="1.0.0",
        description="Simple",
        author="carol",
        download_url="https://example.com/s.zip",
        package_data=b"simple",
    )
    assert p3.security_level == pm.SecurityLevel.MEDIUM


def test_plugin_verification_and_approval(marketplace):
    data = b"signed-package"
    p = marketplace.register_plugin(
        name="secure",
        version="1.0.0",
        description="",
        author="dev",
        download_url="https://example.com/s.zip",
        package_data=data,
    )
    pid = p.id

    assert marketplace.verify_plugin(pid, data) is True
    assert marketplace.approve_plugin(pid) is True
    assert p.status == pm.PluginStatus.APPROVED

    # Wrong package data fails checksum
    assert marketplace.verify_plugin(pid, b"wrong") is False
    assert marketplace.approve_plugin("missing") is False

    # Unverified signature blocks approval
    p.signature.verified = False
    assert marketplace.approve_plugin(pid) is False


def test_plugin_workflow_operations(marketplace):
    p = marketplace.register_plugin(
        name="w",
        version="1.0.0",
        description="w",
        author="dev",
        download_url="https://example.com/w.zip",
        package_data=b"w",
    )
    pid = p.id

    assert marketplace.reject_plugin(pid, "incomplete") is True
    assert p.status == pm.PluginStatus.REJECTED
    assert p.metadata["rejection_reason"] == "incomplete"

    assert marketplace.deprecate_plugin(pid) is True
    assert p.status == pm.PluginStatus.DEPRECATED

    assert marketplace.reject_plugin("missing", "x") is False
    assert marketplace.deprecate_plugin("missing") is False


def test_marketplace_queries(marketplace):
    a = marketplace.register_plugin(
        name="alpha",
        version="1.0.0",
        description="alpha search keyword plugin",
        author="alice",
        download_url="https://example.com/a.zip",
        package_data=b"a",
        metadata={"requires_network": True},
    )
    b = marketplace.register_plugin(
        name="beta",
        version="2.0.0",
        description="beta widget",
        author="bob",
        download_url="https://example.com/b.zip",
        package_data=b"b",
    )
    marketplace.register_plugin(
        name="alpha",
        version="0.9.0",
        description="older alpha",
        author="alice",
        download_url="https://example.com/a09.zip",
        package_data=b"a09",
    )

    all_plugins = marketplace.list_plugins()
    assert len(all_plugins) == 3

    approved = marketplace.list_plugins(status=pm.PluginStatus.APPROVED)
    assert len(approved) == 0

    high = marketplace.list_plugins(security_level=pm.SecurityLevel.HIGH)
    assert len(high) == 1
    assert high[0]["name"] == "alpha"

    by_author = marketplace.list_plugins(author="alice")
    assert len(by_author) == 2

    found = marketplace.search_plugins("keyword")
    assert len(found) == 1
    found2 = marketplace.search_plugins("widget")
    assert len(found2) == 1

    versions = marketplace.get_plugin_versions("alpha")
    assert len(versions) == 2
    assert versions[0]["version"] >= versions[1]["version"]

    assert marketplace.get_plugin("missing") is None
    assert marketplace.get_plugin(a.id)["name"] == "alpha"


def test_check_dependencies_and_statistics(marketplace):
    marketplace.register_plugin(
        name="base",
        version="1.0.0",
        description="base",
        author="dev",
        download_url="https://example.com/base.zip",
        package_data=b"base",
    )
    child = marketplace.register_plugin(
        name="child",
        version="1.0.0",
        description="child",
        author="dev",
        download_url="https://example.com/child.zip",
        package_data=b"child",
        dependencies=["base-1.0.0", "missing-1.0.0"],
    )

    result = marketplace.check_dependencies(child.id)  # noqa: F841  # Variable for test verification
    assert result["valid"] is False
    assert "base-1.0.0" in result["available"]
    assert "missing-1.0.0" in result["missing"]

    assert marketplace.check_dependencies("missing")["valid"] is False

    stats = marketplace.get_statistics()
    assert stats["total_plugins"] == 2
    assert stats["signed_plugins"] == 2


def test_storage_load_and_save(marketplace):
    now = datetime.now().isoformat()
    stored = {
        "base-1.0.0": {
            "id": "base-1.0.0",
            "name": "base",
            "version": "1.0.0",
            "description": "base",
            "author": "dev",
            "status": "approved",
            "security_level": "medium",
            "download_url": "https://example.com/base.zip",
            "checksum": "abc",
            "size_bytes": 4,
            "dependencies": [],
            "signature": None,
            "created_at": now,
            "updated_at": now,
            "metadata": {},
        }
    }
    marketplace.storage.load.return_value = stored
    # Re-initialize to exercise _load_from_storage
    assert marketplace.initialize() is True
    loaded = marketplace.get_plugin("base-1.0.0")
    assert loaded["status"] == "approved"

    # Force save exception
    marketplace.storage.save.side_effect = RuntimeError("storage down")
    marketplace.reject_plugin("base-1.0.0", "x")  # triggers _save_to_storage


def test_create_plugin_marketplace_failure(monkeypatch):
    class _BadMarketplace:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("boom")

    monkeypatch.setattr(pm, "PluginMarketplace", _BadMarketplace)
    assert pm.create_plugin_marketplace() is None


# -----------------------------------------------------------------------------
# core.performance_optimizer
# -----------------------------------------------------------------------------


@pytest.fixture
def po(monkeypatch):
    import psutil

    monkeypatch.setattr(psutil, "cpu_percent", lambda interval=None: 5.0)
    monkeypatch.setattr(psutil, "virtual_memory", lambda: type("M", (), {"percent": 55.0})())
    monkeypatch.setattr(threading.Thread, "start", lambda self: None)
    import core.performance_optimizer as po_module

    return po_module


def test_optimizer_initialization_and_thresholds(po):
    opt = po.PerformanceOptimizer()
    assert opt.thresholds["response_time_warning"] == 1.0
    assert "api_requests" in opt.async_pools
    assert "metrics" in opt.caches
    # The module-level global instance should exist
    assert po.get_performance_optimizer() is po.performance_optimizer


def test_cache_operations(po):
    opt = po.PerformanceOptimizer()
    opt.cache_set("metrics", "key1", "value1")
    assert opt.cache_get("metrics", "key1") == "value1"
    assert opt.cache_stats["metrics"].hits == 1
    assert opt.cache_get("metrics", "missing") is None
    assert opt.cache_stats["metrics"].misses == 1
    assert opt.cache_delete("metrics", "key1") is True
    assert opt.cache_delete("metrics", "key1") is False
    assert opt.cache_delete("missing", "key") is False
    opt.cache_set("alerts", "a", 1)
    opt.cache_set("alerts", "b", 2)
    assert opt.cache_clear("alerts") == 2
    assert opt.cache_clear("missing") == 0


def test_cache_stats_and_report(po):
    opt = po.PerformanceOptimizer()
    assert opt.cache_stats.get("metrics", po.CacheStats(cache_name="metrics")).hit_rate == 0.0
    opt.cache_get("metrics", "none")
    assert opt.cache_stats["metrics"].misses == 1
    report = opt.get_performance_report()
    assert "bottlenecks" in report
    assert "cache_stats" in report
    assert "query_stats" in report
    assert "slow_queries" in report
    assert "performance_alerts" in report
    assert "metrics_summary" in report


@pytest.mark.asyncio
async def test_with_semaphore(po):
    opt = po.PerformanceOptimizer()

    async def _coro(arg, kwarg=None):
        return (arg, kwarg)

    result = await opt.with_semaphore("api_requests", _coro, "hello", kwarg="world")  # noqa: F841  # Variable for test verification
    assert result == ("hello", "world")  # noqa: F841  # Variable for test verification

    unknown = await opt.with_semaphore("unknown", _coro, "x")
    assert unknown == ("x", None)


def test_optimize_database_query(po, monkeypatch):
    opt = po.PerformanceOptimizer()
    mock_time = MagicMock(side_effect=[0.0, 2.5])
    monkeypatch.setattr(po.time, "time", mock_time)

    @opt.optimize_database_query
    def slow_query():
        return {"rows": 10}

    assert slow_query() == {"rows": 10}
    assert "slow_query" in opt.query_stats
    assert len(opt.slow_queries) == 1
    assert opt.slow_queries[0]["function"] == "slow_query"

    mock_time2 = MagicMock(side_effect=[0.0, 0.1])
    monkeypatch.setattr(po.time, "time", mock_time2)

    @opt.optimize_database_query
    def fast_query():
        return 1

    assert fast_query() == 1
    assert opt.query_stats["fast_query"]

    monkeypatch.setattr(po.time, "time", lambda: 0.0)

    @opt.optimize_database_query
    def failing_query():
        raise RuntimeError("fail")

    with pytest.raises(RuntimeError):
        failing_query()


def test_monitor_performance_and_bottlenecks(po):
    opt = po.PerformanceOptimizer()
    opt.monitor_performance("api", po.PerformanceMetric.RESPONSE_TIME, 10.0)
    assert any(b.component == "api" for b in opt.bottlenecks)
    assert any(b.metric == po.PerformanceMetric.RESPONSE_TIME for b in opt.bottlenecks)

    # Non-critical metric
    opt.monitor_performance("worker", po.PerformanceMetric.THROUGHPUT, 100.0)


def test_internal_monitoring_methods(po, monkeypatch):
    opt = po.PerformanceOptimizer()
    now = datetime.now()

    # Build metrics so detection triggers
    opt.metrics_history["response_time"].extend([(now, 12.0)] * 12)
    opt.metrics_history["memory_usage"].extend([(now, 98.0)] * 6)
    opt.metrics_history["cpu_usage"].extend([(now, 95.0)] * 6)
    detected = opt._detect_bottlenecks()
    assert detected["detected_count"] >= 1

    # Alerts
    opt.metrics_history["response_time_alert"].extend([(now, 5.0)] * 12)
    opt.metrics_history["memory_alert"].extend([(now, 90.0)] * 12)
    opt.metrics_history["cpu_alert"].extend([(now, 85.0)] * 12)
    opt.metrics_history["error_rate_alert"].extend([(now, 0.2)] * 12)
    opt._check_alerts()
    assert len(opt.performance_alerts) >= 1

    # Cleanup
    old = now - timedelta(days=2)
    opt.metrics_history["response_time"].append((old, 1.0))
    opt.bottlenecks.append(
        po.PerformanceBottleneck(
            bottleneck_id="old",
            component="x",
            metric=po.PerformanceMetric.CPU_USAGE,
            severity="critical",
            current_value=1.0,
            threshold_value=1.0,
            description="x",
            detected_at=now - timedelta(hours=2),
        )
    )
    opt.performance_alerts.append(
        {
            "alert_id": "old_alert",
            "metric": "x",
            "current_value": 1.0,
            "threshold": 1.0,
            "timestamp": (now - timedelta(hours=8)).isoformat(),
        }
    )
    opt._cleanup_old_metrics()
    assert all(ts > now - timedelta(hours=25) for ts, _ in opt.metrics_history["response_time"])
    assert not any(b.bottleneck_id == "old" for b in opt.bottlenecks)
    assert not any(a.get("alert_id") == "old_alert" for a in opt.performance_alerts)
    assert len(opt.bottlenecks) >= 1
    assert len(opt.performance_alerts) >= 1


def test_optimize_memory_usage(po, monkeypatch):
    opt = po.PerformanceOptimizer()
    opt.cache_set("metrics", "x", 1)
    # Ensure gc.collect is called without side effects
    monkeypatch.setattr("gc.collect", lambda: 0)
    opt.optimize_memory_usage()
    assert opt.cache_get("metrics", "x") is None


def test_cache_missing_and_collect_metrics(po):
    opt = po.PerformanceOptimizer()
    # cache_name not in self.caches
    assert opt.cache_get("missing", "key") is None
    assert opt.cache_set("missing", "key", "value") is None

    # Trigger cache_stats population then collect metrics
    opt.cache_get("metrics", "none")
    opt._collect_metrics()
    assert "cpu_usage" in opt.metrics_history
    assert "memory_usage" in opt.metrics_history


def test_cache_disabled_mode(po, monkeypatch):
    monkeypatch.setattr(po, "CACHING_AVAILABLE", False)
    opt = po.PerformanceOptimizer()
    assert isinstance(opt.caches["metrics"], dict)
    opt.cache_set("metrics", "key", "value")
    assert opt.cache_get("metrics", "key") == "value"
    assert opt.cache_get("metrics", "missing") is None
    assert opt.cache_delete("metrics", "key") is True
    opt.cache_set("metrics", "x", 1)
    assert opt.cache_clear("metrics") == 1


def test_memory_monitor_failure(po, monkeypatch):
    def _boom():
        raise RuntimeError("psutil unavailable")

    monkeypatch.setattr(po.psutil, "virtual_memory", _boom)
    opt = po.PerformanceOptimizer()
    assert opt._initialize_memory_monitor() is False


def test_get_performance_optimizer_with_config(po, monkeypatch):
    monkeypatch.setattr(po, "performance_optimizer", None)
    instance = po.get_performance_optimizer({"foo": "bar"})
    assert isinstance(instance, po.PerformanceOptimizer)


def test_optimize_memory_usage_handles_cache_clear_error(po, monkeypatch):
    opt = po.PerformanceOptimizer()
    opt.cache_set("metrics", "x", 1)
    original = opt.cache_clear

    def _bad_clear(name):
        if name == list(opt.caches.keys())[0]:
            raise RuntimeError("clear boom")
        return original(name)

    monkeypatch.setattr(opt, "cache_clear", _bad_clear)
    monkeypatch.setattr("gc.collect", lambda: 0)
    opt.optimize_memory_usage()


# -----------------------------------------------------------------------------
# core.concurrency_control
# -----------------------------------------------------------------------------


def test_concurrency_control_default():
    assert cc.AGENT_SESSION_LIMIT == 50
    assert cc.agent_session_semaphore is not None

    controller = cc.ConcurrencyController(max_concurrent=2)

    async def _runner():
        async def _coro():
            return "done"

        return await controller.run_with_limit(_coro())

    assert asyncio.run(_runner()) == "done"


def test_concurrency_control_env_override(monkeypatch):
    monkeypatch.setenv("AIOPS_MAX_AGENT_SESSIONS", "7")
    importlib.reload(cc)
    assert cc.AGENT_SESSION_LIMIT == 7
    # Restore default for any subsequent tests in this file
    monkeypatch.delenv("AIOPS_MAX_AGENT_SESSIONS")
    importlib.reload(cc)
    assert cc.AGENT_SESSION_LIMIT == 50
