# -*- coding: utf-8 -*-
"""Functional coverage tests for core uncovered batch 19-b modules."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import logging
import secrets
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError

import core.api_error as api_error
import core.audit_integration_manager as audit_mgr
import core.db_query_optimization as db_opt
import core.hitl.multi_level as ml
import core.interface.grpc.server as grpc_server

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.hitl.multi_level
# ---------------------------------------------------------------------------
def test_multi_level_approval_scenario():
    workflow = ml.ApprovalWorkflow()
    approver = ml.MultiLevelApprover(workflow)

    l1 = ml.ApprovalConfig(
        level=ml.ApprovalLevel.L1,
        approvers=["alice", "bob"],
        timeout_minutes=30,
    )
    l2 = ml.ApprovalConfig(
        level=ml.ApprovalLevel.L2,
        approvers=["carol"],
        required=False,
        timeout_minutes=20,
    )
    approver.configure_level(l1)
    approver.configure_level(l2)

    request = approver.create_multi_level_request(
        workflow_id="wf-1",
        title="Deploy X",
        description="Deploy to production",
        min_level=ml.ApprovalLevel.L1,
        context={"env": "prod"},
    )
    assert request.workflow_id == "wf-1"
    assert request.title == "Deploy X"
    assert len(request.steps) == 3
    step_ids = {s.step_id for s in request.steps}
    assert "l1_0" in step_ids
    assert "l1_1" in step_ids
    assert "l2_0" in step_ids

    # L2 approver is optional and should not appear in required list
    required = approver.get_required_approvers(request.request_id)
    assert "alice" in required
    assert "bob" in required
    assert "carol" not in required

    pending = approver.get_pending_approvals(
        "alice"
    )  # noqa: F841  # Variable for test verification
    assert any(p["request_id"] == request.request_id for p in pending)

    # Edge cases with missing request/approver
    assert approver.get_required_approvers("missing") == []
    assert approver.get_pending_approvals("nobody") == []

    # Minimum level L2 should skip L1 steps
    request2 = approver.create_multi_level_request(
        workflow_id="wf-2",
        title="Minor",
        description="Minor change",
        min_level=ml.ApprovalLevel.L2,
    )
    assert len(request2.steps) == 1
    assert request2.steps[0].step_id == "l2_0"


# ---------------------------------------------------------------------------
# core.api_error
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_api_error_handler_scenarios():
    request = MagicMock(method="GET", url=MagicMock(path="/api/x"))
    expected = {
        400: "VALIDATION_ERROR",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        500: "INTERNAL_ERROR",
        503: "INTERNAL_ERROR",
    }
    for status, code in expected.items():
        exc = HTTPException(status_code=status, detail=f"error {status}")
        response = await api_error.api_error_handler(request, exc)
        assert response.status_code == status
        body = json.loads(response.body)
        assert body["success"] is False
        assert body["error"]["code"] == code
        assert body["error"]["message"] == f"error {status}"


@pytest.mark.asyncio
async def test_validation_error_handler():
    request = MagicMock(method="POST", url=MagicMock(path="/api/y"))
    exc = RequestValidationError(
        [
            {
                "loc": ("query", "q"),
                "msg": "field required",
                "type": "value_error.missing",
            }
        ]
    )
    response = await api_error.validation_error_handler(request, exc)
    assert response.status_code == 422
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "field required" in body["error"]["details"]


@pytest.mark.asyncio
async def test_general_exception_handler_debug(monkeypatch):
    request = MagicMock(method="GET", url=MagicMock(path="/api/z"))
    monkeypatch.setattr(api_error.logger, "level", logging.DEBUG)
    response = await api_error.general_exception_handler(request, RuntimeError("boom"))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_ERROR"
    assert body["error"]["details"] == "boom"


@pytest.mark.asyncio
async def test_general_exception_handler_no_debug(monkeypatch):
    request = MagicMock(method="GET", url=MagicMock(path="/api/z"))
    monkeypatch.setattr(api_error.logger, "level", logging.INFO)
    response = await api_error.general_exception_handler(request, RuntimeError("boom"))
    assert response.status_code == 500
    body = json.loads(response.body)
    assert body["success"] is False
    assert body["error"]["details"] is None


# ---------------------------------------------------------------------------
# core.audit_integration_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def audit_instance(tmp_path, monkeypatch):
    """Provide an isolated AuditIntegrationManager with fast, deterministic internals."""
    monkeypatch.setattr(audit_mgr.asyncio, "sleep", AsyncMock())

    class FakeRandom:
        def __init__(self, *args, **kwargs):
            pass

        def randint(self, a, b):
            return 2

        def choice(self, seq):
            return seq[0]

    monkeypatch.setattr(secrets, "SystemRandom", FakeRandom)

    return audit_mgr.AuditIntegrationManager(
        config={
            "storage_dir": str(tmp_path / "audit"),
            "max_trails": 3,
            "auto_collection": False,
        }
    )


@pytest.mark.asyncio
async def test_audit_collect_and_query(audit_instance, tmp_path):
    mgr = audit_instance

    # Register an extra source to exercise registration path
    extra = audit_mgr.AuditSource(
        source_id="extra",
        source_name="Extra Source",
        category=audit_mgr.AuditCategory.OPERATIONAL,
        endpoint="internal://extra",
    )
    mgr.register_source(extra)
    assert "extra" in mgr.audit_sources

    # Collect from all enabled sources (5 sources, 2 trails each)
    trail_ids = await mgr.collect_audit_trails()
    assert len(trail_ids) == 10
    assert len(mgr.audit_trails) == 3  # max_trails prune applied

    # Filtered collections
    assert len(await mgr.collect_audit_trails(source_id="security_audit")) == 2
    assert len(await mgr.collect_audit_trails(category=audit_mgr.AuditCategory.SECURITY)) >= 2
    assert await mgr.collect_audit_trails(source_id="ghost") == []

    # Manually add a trail
    trail = audit_mgr.AuditTrail(
        trail_id="t1",
        source_id="security_audit",
        category=audit_mgr.AuditCategory.SECURITY,
        event_type="login",
        action="user login",
        user_id="u1",
    )
    tid = await mgr.add_audit_trail(trail)
    assert tid == "t1"

    # Report generation and persistence
    start = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end = datetime(2030, 1, 1, tzinfo=timezone.utc)
    report = await mgr.generate_audit_report(
        period_start=start,
        period_end=end,
        categories=[audit_mgr.AuditCategory.SECURITY],
    )
    assert report.total_events >= 1
    assert report.report_id in mgr.audit_reports
    assert (tmp_path / "audit" / f"{report.report_id}.json").exists()

    # Query with all filters
    results = mgr.query_trails(
        source_id="security_audit",
        category=audit_mgr.AuditCategory.SECURITY,
        event_type="login",
        user_id="u1",
        start_time=start,
        end_time=end,
        limit=10,
    )
    assert any(r["trail_id"] == "t1" for r in results)

    # Statistics
    stats = mgr.get_statistics()
    assert stats["total_sources"] == 5
    assert stats["total_trails"] > 0
    assert stats["total_reports"] == 1


@pytest.mark.asyncio
async def test_audit_collect_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_mgr.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(secrets, "SystemRandom", MagicMock(side_effect=RuntimeError("boom")))
    mgr = audit_mgr.AuditIntegrationManager(
        config={"storage_dir": str(tmp_path / "audit"), "auto_collection": False}
    )
    trail_ids = await mgr.collect_audit_trails(source_id="security_audit")
    assert trail_ids == []
    assert len(mgr.audit_sources) == 4


async def test_audit_auto_collection_and_handlers(audit_instance, monkeypatch):
    mgr = audit_instance

    # auto_collection is disabled in the fixture, so this returns immediately
    await mgr.start_auto_collection()

    # Enable auto_collection and verify it starts the background task
    mgr.auto_collection = True
    task_spy = MagicMock(side_effect=lambda coro: coro.close() if hasattr(coro, "close") else None)
    monkeypatch.setattr(audit_mgr.asyncio, "create_task", task_spy)
    await mgr.start_auto_collection()
    assert task_spy.called

    # Alert handlers and factory
    handler = MagicMock()
    mgr.register_alert_handler(handler)
    assert handler in mgr.alert_handlers

    factory = audit_mgr.get_audit_integration_manager(
        config={"storage_dir": str(audit_instance.config["storage_dir"])}
    )
    assert isinstance(factory, audit_mgr.AuditIntegrationManager)


# ---------------------------------------------------------------------------
# core.interface.grpc.server
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_grpc_server(monkeypatch):
    """Replace grpc.server and ThreadPoolExecutor with fakes."""
    monkeypatch.setattr(grpc_server.futures, "ThreadPoolExecutor", MagicMock())

    fake_server = MagicMock()
    fake_server.add_insecure_port = MagicMock(return_value=None)
    fake_server.start = MagicMock(return_value=None)
    fake_server.stop = MagicMock(return_value=None)
    fake_server.wait_for_termination = AsyncMock(return_value=None)

    fake_grpc = MagicMock()
    fake_grpc.server = MagicMock(return_value=fake_server)
    monkeypatch.setattr(grpc_server, "grpc", fake_grpc)
    return fake_server


@pytest.mark.asyncio
async def test_grpc_server_start_stop_wait(fake_grpc_server):
    server = grpc_server.AIOpsGrpcServer(host="0.0.0.0", port=1234, max_workers=4)
    await server.start()
    assert server._server is fake_grpc_server
    fake_grpc_server.add_insecure_port.assert_called_once_with("0.0.0.0:1234")
    fake_grpc_server.start.assert_called_once()

    await server.wait_for_termination()
    fake_grpc_server.wait_for_termination.assert_awaited_once()

    await server.stop()
    fake_grpc_server.stop.assert_called_once_with(grace=5)


@pytest.mark.asyncio
async def test_grpc_server_start_failure(monkeypatch):
    monkeypatch.setattr(grpc_server.futures, "ThreadPoolExecutor", MagicMock())
    fake_grpc = MagicMock()
    fake_grpc.server = MagicMock(side_effect=RuntimeError("bind failed"))
    monkeypatch.setattr(grpc_server, "grpc", fake_grpc)

    server = grpc_server.AIOpsGrpcServer()
    with pytest.raises(RuntimeError, match="bind failed"):
        await server.start()


@pytest.mark.asyncio
async def test_grpc_server_stop_wait_without_start():
    server = grpc_server.AIOpsGrpcServer()
    await server.stop()
    await server.wait_for_termination()
    assert server._server is None


# ---------------------------------------------------------------------------
# core.db_query_optimization
# ---------------------------------------------------------------------------
def test_query_cache_basic():
    cache = db_opt.QueryCache(ttl_seconds=-1)
    assert cache.get("missing") is None

    cache.set("k1", "v1")
    # ttl is -1, so the entry is already expired
    assert cache.get("k1") is None

    cache2 = db_opt.QueryCache(ttl_seconds=300)
    cache2.set("k2", "v2")
    assert cache2.get("k2") == "v2"

    cache2.invalidate("k2")
    assert cache2.get("k2") is None

    cache2.set("k3", "v3")
    cache2.invalidate()
    assert cache2.get("k3") is None
    assert cache2.cache == {}


def test_query_cache_cleanup_expired():
    cache = db_opt.QueryCache(ttl_seconds=-1)
    cache.set("old", 1)
    cache.set("older", 2)
    cache.set("fresh", 3)
    # all entries are expired because ttl is negative
    cache.cleanup_expired()
    assert cache.cache == {}


@pytest.mark.asyncio
async def test_cache_query_result_decorator(monkeypatch):
    cache = db_opt.QueryCache(ttl_seconds=300)
    monkeypatch.setattr(db_opt, "query_cache", cache)

    call_count = 0

    @db_opt.cache_query_result(ttl_seconds=60)
    async def heavy(x):
        nonlocal call_count
        call_count += 1
        return x * 2

    assert await heavy(5) == 10
    assert call_count == 1

    # Second call with same args should be a cache hit
    assert await heavy(5) == 10
    assert call_count == 1

    # Different arg misses cache
    assert await heavy(7) == 14
    assert call_count == 2


@pytest.mark.asyncio
async def test_batch_query_optimizer_success():
    session = AsyncMock()
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)

    model_class = MagicMock(return_value=MagicMock())
    items = [{"name": "a"}, {"name": "b"}, {"name": "c"}]

    result = await db_opt.BatchQueryOptimizer.batch_insert(  # noqa: F841  # Variable for test verification
        session, model_class, items, batch_size=2
    )
    assert result["total"] == 3
    assert result["inserted"] == 3
    assert result["failed"] == 0
    assert result["batches"] == 2

    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_batch_query_optimizer_insert_failure():
    session = AsyncMock()
    session.commit = AsyncMock(side_effect=RuntimeError("commit failed"))
    session.rollback = AsyncMock(return_value=None)

    model_class = MagicMock(return_value=MagicMock())
    items = [{"name": "a"}, {"name": "b"}]

    result = await db_opt.BatchQueryOptimizer.batch_insert(  # noqa: F841  # Variable for test verification
        session, model_class, items, batch_size=1
    )
    assert result["total"] == 2
    assert result["inserted"] == 0
    assert result["failed"] == 2
    assert result["batches"] == 2
    session.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_batch_query_optimizer_update(monkeypatch):
    select_mock = MagicMock()
    select_mock.where = MagicMock(return_value=select_mock)
    monkeypatch.setattr(db_opt, "select", MagicMock(return_value=select_mock))

    instance = type("Instance", (), {})()
    none_result = MagicMock()  # noqa: F841  # Variable for test verification
    none_result.scalar_one_or_none = MagicMock(return_value=None)
    found_result = MagicMock()  # noqa: F841  # Variable for test verification
    found_result.scalar_one_or_none = MagicMock(return_value=instance)

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=[found_result, none_result])
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)

    model_class = type("Model", (), {"id": 1})
    updates = [{"id": 1, "name": "new"}, {"id": 2, "name": "missing"}]

    result = await db_opt.BatchQueryOptimizer.batch_update(  # noqa: F841  # Variable for test verification
        session, model_class, updates, id_field="id", batch_size=10
    )
    assert result["total"] == 2
    assert result["updated"] == 2
    assert result["failed"] == 0
    assert getattr(instance, "name") == "new"


@pytest.mark.asyncio
async def test_batch_query_optimizer_update_failure(monkeypatch):
    select_mock = MagicMock()
    select_mock.where = MagicMock(return_value=select_mock)
    monkeypatch.setattr(db_opt, "select", MagicMock(return_value=select_mock))

    session = AsyncMock()
    session.execute = AsyncMock(side_effect=RuntimeError("query failed"))
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)

    model_class = type("Model", (), {"id": 1})
    updates = [{"id": 1, "name": "new"}]

    result = await db_opt.BatchQueryOptimizer.batch_update(  # noqa: F841  # Variable for test verification
        session, model_class, updates, batch_size=1
    )
    assert result["total"] == 1
    assert result["updated"] == 0
    assert result["failed"] == 1
    session.rollback.assert_awaited()


def _make_fake_session_context(session):
    class FakeContext:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    return FakeContext()


@pytest.mark.asyncio
async def test_connection_pool_monitor(monkeypatch):
    monkeypatch.setattr(db_opt, "text", lambda query: query)
    session = AsyncMock()
    result = MagicMock()  # noqa: F841  # Variable for test verification
    result.fetchone = MagicMock(return_value=(10, 3, 7))
    session.execute = AsyncMock(return_value=result)
    monkeypatch.setattr(db_opt, "AsyncSessionLocal", lambda: _make_fake_session_context(session))

    stats = await db_opt.ConnectionPoolMonitor.get_pool_stats()
    assert stats["total_connections"] == 10
    assert stats["active_connections"] == 3
    assert stats["idle_connections"] == 7

    healthy = await db_opt.ConnectionPoolMonitor.check_pool_health()
    assert healthy["healthy"] is True

    # Unhealthy thresholds
    result.fetchone = MagicMock(return_value=(100, 10, 90))
    unhealthy = await db_opt.ConnectionPoolMonitor.check_pool_health()
    assert unhealthy["healthy"] is False

    # Error path
    session.execute = AsyncMock(side_effect=RuntimeError("db down"))
    error_stats = await db_opt.ConnectionPoolMonitor.get_pool_stats()
    assert "error" in error_stats


@pytest.mark.asyncio
async def test_optimize_database_queries(monkeypatch):
    cache = db_opt.QueryCache(ttl_seconds=60)
    monkeypatch.setattr(db_opt, "query_cache", cache)
    monkeypatch.setattr(
        db_opt.ConnectionPoolMonitor,
        "check_pool_health",
        AsyncMock(return_value={"healthy": True}),
    )

    result = (
        await db_opt.optimize_database_queries()
    )  # noqa: F841  # Variable for test verification
    assert result["cache_cleanup"] == "completed"
    assert "healthy" in str(result["pool_health"])

    # Exception path
    monkeypatch.setattr(
        db_opt.ConnectionPoolMonitor,
        "check_pool_health",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    result = (
        await db_opt.optimize_database_queries()
    )  # noqa: F841  # Variable for test verification
    assert "error" in result
    assert result["cache_cleanup"] == "completed"
