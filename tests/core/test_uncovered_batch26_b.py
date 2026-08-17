# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 26-b modules."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import hashlib
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import subprocess
import sys  # noqa: F401  # Imported for test setup
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.audit_service helpers
# ---------------------------------------------------------------------------
class _FakeAuditLog:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "id"):
            self.id = 1
        if not hasattr(self, "created_at"):
            self.created_at = datetime.datetime.now()


class _FakeResult:
    def __init__(self, all_logs=None, count=0, one=None, rows=None, rowcount=0):
        self._all = all_logs or []
        self._count = count
        self._one = one
        self._rows = rows or []
        self._rowcount = rowcount

    def scalars(self):
        return self

    def all(self):
        return self._all

    def scalar(self):
        return self._count

    def scalar_one_or_none(self):
        return self._one

    def __iter__(self):
        return iter(self._rows)

    @property
    def rowcount(self):
        return self._rowcount


class _FakeSession:
    def __init__(self, result=None):
        self.result = result or _FakeResult()  # noqa: F841  # Variable for test verification
        self.added = []
        self.committed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.committed = True

    async def refresh(self, obj):
        if getattr(obj, "id", None) is None:
            obj.id = 1

    async def execute(self, stmt):
        return self.result


class _AsyncSessionFactory:
    def __init__(self, result=None):
        self.result = result or _FakeResult()  # noqa: F841  # Variable for test verification

    def __call__(self):
        return _FakeSession(self.result)


def _patch_audit_session(monkeypatch, **kwargs):
    monkeypatch.setattr(
        "core.audit_service.AsyncSessionLocal", _AsyncSessionFactory(_FakeResult(**kwargs))
    )
    monkeypatch.setattr("core.audit_service.DATA_PRIVACY_AVAILABLE", False)
    monkeypatch.setattr("core.audit_service.anonymize_dict", None)


# ---------------------------------------------------------------------------
# core.audit_service
# ---------------------------------------------------------------------------
@pytest.fixture
def audit_service_module():
    import core.audit_service as audit_service

    return audit_service


@pytest.mark.asyncio
async def test_audit_log_action_success(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch)

    log_id = await audit_service_module.AuditService.log_action(
        action="login",
        resource_type="user",
        resource_id="u1",
        user_id=1,
        username="admin",
        ip_address="127.0.0.1",
        status="success",
        details="details",
        metadata={"extra": 1},
    )
    assert log_id == 1


@pytest.mark.asyncio
async def test_audit_log_action_security_event(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch)

    log_id = await audit_service_module.AuditService.log_action(
        action="login_failure",
        resource_type="auth",
        status="failure",
        username="admin",
    )
    assert log_id == 1


@pytest.mark.asyncio
async def test_audit_log_action_exception(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch)
    import core.audit_service as audit_service

    class BadSessionFactory:
        def __call__(self):
            raise RuntimeError("db down")

    monkeypatch.setattr(audit_service, "AsyncSessionLocal", BadSessionFactory())
    log_id = await audit_service_module.AuditService.log_action(
        action="login", resource_type="user"
    )
    assert log_id is None


@pytest.mark.asyncio
async def test_audit_get_audit_logs(audit_service_module, monkeypatch):
    now = datetime.datetime.now()
    fake_logs = [
        _FakeAuditLog(
            id=i,
            action="login",
            resource_type="user",
            resource_id=f"u{i}",
            user_id=i,
            username="admin",
            ip_address="127.0.0.1",
            success=True,
            error_message="details",
            changes={"x": i},
            created_at=now,
        )
        for i in range(1, 3)
    ]
    _patch_audit_session(monkeypatch, all_logs=fake_logs)

    logs = await audit_service_module.AuditService.get_audit_logs(
        action="login",
        resource_type="user",
        resource_id="u1",
        username="admin",
        start_date=now - datetime.timedelta(days=1),
        end_date=now + datetime.timedelta(days=1),
    )
    assert len(logs) == 2


@pytest.mark.asyncio
async def test_audit_count_audit_logs(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, count=42)
    count = await audit_service_module.AuditService.count_audit_logs(
        action="login", resource_type="user", username="admin"
    )
    assert count == 42


@pytest.mark.asyncio
async def test_audit_user_activity_summary(audit_service_module, monkeypatch):
    rows = [SimpleNamespace(action="login", count=5)]
    _patch_audit_session(monkeypatch, count=10, rows=rows)
    summary = await audit_service_module.AuditService.get_user_activity_summary("admin", days=7)
    assert summary["username"] == "admin"
    assert summary["total_actions"] == 10
    assert summary["actions_by_type"]["login"] == 5


@pytest.mark.asyncio
async def test_audit_cleanup_old_logs_with_deletion(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, count=3)
    deleted = await audit_service_module.AuditService.cleanup_old_logs(days_to_keep=7)
    assert deleted == 3


@pytest.mark.asyncio
async def test_audit_cleanup_old_logs_no_deletion(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, count=0)
    deleted = await audit_service_module.AuditService.cleanup_old_logs(days_to_keep=7)
    assert deleted == 0


@pytest.mark.asyncio
async def test_audit_detect_suspicious_activity(audit_service_module, monkeypatch):
    now = datetime.datetime.now()
    fake_logs = [
        _FakeAuditLog(
            action="login_failure", success=False, ip_address=f"10.0.0.{i % 4}", created_at=now
        )
        for i in range(5)
    ] + [
        _FakeAuditLog(
            action="permission_denied", success=False, ip_address="10.0.0.1", created_at=now
        )
        for _ in range(3)
    ]
    _patch_audit_session(monkeypatch, all_logs=fake_logs)
    result = await audit_service_module.AuditService.detect_suspicious_activity("admin", hours=24)  # noqa: F841  # Variable for test verification
    types = [r["type"] for r in result]
    assert "multiple_failed_logins" in types
    assert "multiple_permission_denied" in types
    assert "multiple_ip_addresses" in types


@pytest.mark.asyncio
async def test_audit_detect_suspicious_activity_no_results(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, all_logs=[])
    result = await audit_service_module.AuditService.detect_suspicious_activity("admin")  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


def test_audit_detect_security_event(audit_service_module):
    sec = audit_service_module.detect_security_event("login_failure", {"ip": "1.2.3.4"})
    assert sec["is_security_event"] is True
    assert sec["severity"] == "critical"

    normal = audit_service_module.detect_security_event("view", {})
    assert normal["is_security_event"] is False


def test_audit_verify_log_integrity(audit_service_module):
    assert audit_service_module.verify_log_integrity({"hash": "abc"}) is True
    assert audit_service_module.verify_log_integrity({}) is False
    assert audit_service_module.verify_log_integrity(1) is True
    assert audit_service_module.verify_log_integrity(None) is False


@pytest.mark.asyncio
async def test_audit_verify_log_integrity_db_match(audit_service_module, monkeypatch):
    now = datetime.datetime.now()
    action, resource_type, resource_id, username = "login", "user", "u1", "admin"
    status = "success"
    error_message = "details"
    integrity_data = (
        f"{action}:{resource_type}:{resource_id}:{username}:"
        f"{status}:{error_message}:{now.isoformat()}"
    )
    stored_hash = hashlib.sha256(integrity_data.encode()).hexdigest()
    fake_log = _FakeAuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        username=username,
        success=True,
        error_message=error_message,
        created_at=now,
        changes={"_integrity_hash": stored_hash},
    )
    _patch_audit_session(monkeypatch, one=fake_log)
    assert await audit_service_module.verify_log_integrity_db(1) is True


@pytest.mark.asyncio
async def test_audit_verify_log_integrity_db_mismatch(audit_service_module, monkeypatch):
    fake_log = _FakeAuditLog(
        id=1,
        action="login",
        resource_type="user",
        resource_id="u1",
        username="admin",
        success=True,
        error_message="details",
        created_at=datetime.datetime.now(),
        changes={"_integrity_hash": "badhash"},
    )
    _patch_audit_session(monkeypatch, one=fake_log)
    assert await audit_service_module.verify_log_integrity_db(1) is False


@pytest.mark.asyncio
async def test_audit_verify_log_integrity_db_missing(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, one=None)
    assert await audit_service_module.verify_log_integrity_db(1) is False


@pytest.mark.asyncio
async def test_audit_cleanup_old_audit_logs(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch, rowcount=7)
    deleted = await audit_service_module.cleanup_old_audit_logs(days_to_keep=30)
    assert deleted == 7


@pytest.mark.asyncio
async def test_audit_context_success(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch)
    async with audit_service_module.audit_context(action="view", resource_type="alert"):
        pass


@pytest.mark.asyncio
async def test_audit_context_failure(audit_service_module, monkeypatch):
    _patch_audit_session(monkeypatch)
    with pytest.raises(ValueError):
        async with audit_service_module.audit_context(action="delete", resource_type="alert"):
            raise ValueError("boom")


def test_audit_redact_details(audit_service_module, monkeypatch):
    monkeypatch.setattr("core.audit_service.DATA_PRIVACY_AVAILABLE", False)
    assert audit_service_module._redact_details("d", {"m": 1}) == ("d", {"m": 1})
    monkeypatch.setattr("core.audit_service.DATA_PRIVACY_AVAILABLE", True)
    monkeypatch.setattr("core.audit_service.anonymize_dict", lambda x: {"masked": True})
    assert audit_service_module._redact_details("d", {"m": 1}) == (
        {"masked": True},
        {"masked": True},
    )


# ---------------------------------------------------------------------------
# core.call_chain_analysis_engine
# ---------------------------------------------------------------------------
@pytest.fixture
def cce():
    from core.call_chain_analysis_engine import CallChainAnalysisEngine

    return CallChainAnalysisEngine()


def _make_span(span_id, trace_id, operation, duration=10.0, status="ok", **kwargs):
    from core.call_chain_analysis_engine import Span, SpanStatus

    start = datetime.datetime.now(datetime.timezone.utc)
    end = start + datetime.timedelta(milliseconds=duration) if duration else None
    return Span(
        span_id=span_id,
        trace_id=trace_id,
        operation_name=operation,
        start_time=start,
        end_time=end,
        duration_ms=duration,
        status=SpanStatus(status),
        **kwargs,
    )


def _make_trace(trace_id, spans):
    from core.call_chain_analysis_engine import Trace

    trace = Trace(trace_id=trace_id, root_span_id="root")
    for s in spans:
        trace.add_span(s)
    return trace


def test_cce_span_properties():
    from core.call_chain_analysis_engine import Span, SpanKind, SpanStatus

    s = _make_span("s1", "t1", "op", duration=0.0, status="error")
    assert s.is_error is True
    assert s.is_completed is False
    s.end_time = datetime.datetime.now(datetime.timezone.utc)
    assert s.is_completed is True


def test_cce_add_trace_and_analyze(cce):
    s1 = _make_span("s1", "t1", "root", duration=100.0, attributes={"service.name": "svc"})
    s2 = _make_span("s2", "t1", "child", duration=50.0, parent_span_id="s1")
    trace = _make_trace("t1", [s1, s2])
    cce.add_trace(trace)
    analysis = cce.analyze_trace("t1")
    assert analysis["trace_id"] == "t1"
    assert analysis["total_spans"] == 2
    assert analysis["error_count"] == 0
    assert cce.analyze_trace("missing") == {"error": "Trace not found"}


def test_cce_build_tree(cce):
    s1 = _make_span("s1", "t1", "root", duration=100.0)
    s2 = _make_span("s2", "t1", "child", duration=50.0, parent_span_id="s1")
    s3 = _make_span("s3", "t1", "orphan", duration=10.0)
    trace = _make_trace("t1", [s1, s2, s3])
    tree = trace.get_span_tree()
    assert "s1" in tree


def test_cce_root_cause_and_issues(cce):
    from core.call_chain_analysis_engine import SpanStatus

    s1 = _make_span("s1", "t1", "root", duration=2000.0, attributes={"service.name": "svc"})
    s2 = _make_span(
        "s2",
        "t1",
        "db",
        duration=2500.0,
        status="error",
        status_message="timeout",
        parent_span_id="s1",
    )
    trace = _make_trace("t1", [s1, s2])
    cce.add_trace(trace)
    analysis = cce.analyze_trace("t1")
    assert len(analysis["performance_issues"]) > 0
    assert analysis["root_cause"]["root_cause"] == "timeout"


def test_cce_aggregate_and_stats(cce):
    t1 = _make_trace("t1", [_make_span("a", "t1", "op", 10.0)])
    t2 = _make_trace("t2", [_make_span("b", "t2", "op", 20.0)])
    cce.add_trace(t1)
    cce.add_trace(t2)
    agg = cce.aggregate_traces(["t1", "t2", "missing"])
    assert agg["trace_count"] == 2
    assert cce.get_engine_statistics()["total_traces"] == 2


def test_cce_filters(cce):
    from core.call_chain_analysis_engine import SpanStatus

    start = datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(2025, 12, 31, tzinfo=datetime.timezone.utc)

    t1 = _make_trace(
        "t1",
        [
            _make_span("a", "t1", "op", 100.0, attributes={"service.name": "svc1"}),
            _make_span("b", "t1", "error", 50.0, status="error", tags={"env": "prod"}),
        ],
    )
    t2 = _make_trace(
        "t2",
        [_make_span("c", "t2", "op", 3000.0, attributes={"service.name": "svc2"})],
    )
    cce.add_trace(t1)
    cce.add_trace(t2)

    t1.start_time = datetime.datetime(2025, 6, 15, tzinfo=datetime.timezone.utc)
    t2.start_time = datetime.datetime(2025, 6, 15, tzinfo=datetime.timezone.utc)

    assert len(cce.filter_by_service_name("svc1")) == 1
    assert len(cce.filter_by_time_range(start, end)) == 2
    assert len(cce.filter_by_duration(min_duration_ms=2000.0)) == 1
    assert len(cce.filter_by_duration(max_duration_ms=500.0)) == 1
    assert len(cce.filter_by_tags({"env": "prod"})) == 1
    assert len(cce.filter_by_error_status(True)) == 1
    assert len(cce.filter_by_error_status(False)) == 1
    assert len(cce.search_spans_by_operation("error")) == 1


def test_cce_advanced_search(cce):
    t1 = _make_trace(
        "t1",
        [
            _make_span("a", "t1", "op", 100.0, attributes={"service.name": "svc"}),
            _make_span("b", "t1", "child", 200.0, tags={"env": "prod"}),
        ],
    )
    cce.add_trace(t1)
    found = cce.advanced_search(
        trace_id="t1",
        service_name="svc",
        min_duration_ms=50.0,
        max_duration_ms=500.0,
        tags={"env": "prod"},
        has_errors=False,
        operation_name="op",
    )
    assert len(found) == 1


def test_cce_bottlenecks(cce):
    from core.call_chain_analysis_engine import SpanStatus

    t1 = _make_trace(
        "t1",
        [
            _make_span("a", "t1", "slow", 6000.0, attributes={"service.name": "svc"}),
            _make_span("b", "t1", "fast", 10.0),
        ],
    )
    cce.add_trace(t1)
    bottlenecks = cce.identify_performance_bottlenecks()
    assert len(bottlenecks) == 1
    assert bottlenecks[0].severity == "high"


def test_cce_global_instance():
    from core.call_chain_analysis_engine import (
        CallChainAnalysisEngine,
        get_call_chain_analysis_engine,
    )

    e1 = get_call_chain_analysis_engine()
    assert isinstance(e1, CallChainAnalysisEngine)
    e2 = get_call_chain_analysis_engine()
    assert e1 is e2


# ---------------------------------------------------------------------------
# core.api_throughput_optimizer
# ---------------------------------------------------------------------------
@pytest.fixture
def optimizer():
    from core.api_throughput_optimizer import APIThroughputOptimizer

    return APIThroughputOptimizer({"default_concurrent_limit": 50})


def test_api_rate_limit_strategies(optimizer):
    from core.api_throughput_optimizer import RateLimitStrategy

    optimizer.set_rate_limit("/api", 10, 20, RateLimitStrategy.TOKEN_BUCKET)
    optimizer.rate_limit_state["/api"]["tokens"] = 5
    assert optimizer.check_rate_limit("/api", tokens=1) is True
    for _ in range(4):
        assert optimizer.check_rate_limit("/api", tokens=1) is True
    assert optimizer.check_rate_limit("/api", tokens=1) is False

    optimizer.set_rate_limit("/sliding", 5, 10, RateLimitStrategy.SLIDING_WINDOW)
    for _ in range(5):
        assert optimizer.check_rate_limit("/sliding") is True
    assert optimizer.check_rate_limit("/sliding") is False

    optimizer.set_rate_limit("/fixed", 3, 10, RateLimitStrategy.FIXED_WINDOW)
    for _ in range(3):
        assert optimizer.check_rate_limit("/fixed", tokens=1) is True
    assert optimizer.check_rate_limit("/fixed", tokens=1) is False

    assert optimizer.check_rate_limit("/unknown") is True


def test_api_backend_servers(optimizer):
    from core.api_throughput_optimizer import (
        BackendServer,
        LoadBalancingStrategy,
    )

    optimizer.add_backend_server("s1", "10.0.0.1", 80, weight=2)
    optimizer.add_backend_server("s2", "10.0.0.2", 80, weight=1)
    s1 = optimizer.get_backend_server()
    assert s1 is not None
    s2 = optimizer.get_backend_server()
    assert s2 is not None

    optimizer.load_balancing_strategy = LoadBalancingStrategy.LEAST_CONNECTIONS
    s1.current_connections = 5
    s2.current_connections = 1
    least = optimizer.get_backend_server()
    assert least.server_id == "s2"

    optimizer.load_balancing_strategy = LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN
    picked = optimizer.get_backend_server()
    assert picked in optimizer.backend_servers

    optimizer.load_balancing_strategy = LoadBalancingStrategy.IP_HASH
    ip = optimizer.get_backend_server(client_ip="1.2.3.4")
    assert ip is not None

    optimizer.load_balancing_strategy = LoadBalancingStrategy.CONSISTENT_HASH
    default = optimizer.get_backend_server()
    assert default is not None

    for server in optimizer.backend_servers:
        server.is_healthy = False
    assert optimizer.get_backend_server() is None


def test_api_concurrent_and_track(optimizer):
    optimizer.set_concurrent_limit("/api", 2)
    assert optimizer.check_concurrent_limit("/api") is True
    assert optimizer.check_concurrent_limit("/api") is True
    assert optimizer.check_concurrent_limit("/api") is False
    optimizer.release_connection("/api")
    assert optimizer.check_concurrent_limit("/api") is True
    optimizer.release_connection("/api")

    optimizer.track_request("/api", "GET", True, 120.0)
    optimizer.track_request("/api", "GET", False, 300.0)
    metrics = optimizer.get_throughput_metrics("/api", "GET")
    assert metrics is not None
    assert metrics.total_requests == 2

    all_metrics = optimizer.get_all_throughput_metrics()
    assert "GET:/api" in all_metrics


def test_api_optimize_and_stats(optimizer):
    optimizer.set_rate_limit("/api", 100, 200)
    optimizer.set_concurrent_limit("/api", 10)
    for _ in range(5):
        optimizer.track_request("/api", "GET", True, 600.0)
    recs = optimizer.optimize_throughput("/api", "GET")
    assert "recommendations" in recs

    stats = optimizer.get_statistics()
    assert stats["total_requests_processed"] == 5


def test_api_factory():
    from core.api_throughput_optimizer import get_api_throughput_optimizer

    opt = get_api_throughput_optimizer({"default_concurrent_limit": 10})
    assert opt is not None


# ---------------------------------------------------------------------------
# core.data_integration_manager
# ---------------------------------------------------------------------------
@pytest.fixture
def dim_manager(tmp_path):
    from core.data_integration_manager import DataIntegrationManager

    return DataIntegrationManager({"storage_dir": str(tmp_path), "max_records": 1})


@pytest.mark.asyncio
async def test_dim_ingest_and_retrieve(dim_manager, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    rid = await dim_manager.ingest_data(
        "user_data",
        {"name": "Alice", "email": "alice@example.com", "ssn": "123456789"},
    )
    assert rid is not None
    data = await dim_manager.retrieve_data(rid, user_id="u1")
    assert data["record_id"] == rid
    assert data["content"]["ssn"][0] == "1"
    assert data["content"]["ssn"][-1] == "9"


@pytest.mark.asyncio
async def test_dim_ingest_public_and_query(dim_manager, monkeypatch):
    from core.data_integration_manager import DataSensitivity

    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    rid = await dim_manager.ingest_data(
        "log_data", {"message": "hello"}, sensitivity=DataSensitivity.PUBLIC
    )
    records = dim_manager.query_data(source_id="log_data")
    assert any(r["record_id"] == rid for r in records)

    with pytest.raises(ValueError):
        await dim_manager.ingest_data("missing", {})


@pytest.mark.asyncio
async def test_dim_pruning_and_storage(dim_manager, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    r1 = await dim_manager.ingest_data("metrics_data", {"v": 1})
    r2 = await dim_manager.ingest_data("metrics_data", {"v": 2})
    assert r1 in dim_manager.data_records or r2 in dim_manager.data_records
    assert dim_manager.total_records == 2


@pytest.mark.asyncio
async def test_dim_sync_data(dim_manager, monkeypatch):
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    result = await dim_manager.sync_data("user_data")  # noqa: F841  # Variable for test verification
    assert result["total_records_synced"] >= 0
    assert "user_data" in result["sources"]

    result_all = await dim_manager.sync_data()
    assert result_all["total_records_synced"] >= 0


@pytest.mark.asyncio
async def test_dim_auto_sync(dim_manager, monkeypatch):
    dim_manager.auto_sync = True
    dim_manager.sync_interval = 0
    captured = []
    original = asyncio.create_task

    def capture(coro):
        captured.append(coro)
        return MagicMock(cancel=MagicMock())

    monkeypatch.setattr(asyncio, "create_task", capture)
    await dim_manager.start_auto_sync()
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_dim_access_handlers(dim_manager, monkeypatch):
    from core.data_integration_manager import DataSensitivity

    monkeypatch.setattr(asyncio, "sleep", AsyncMock())
    handler_sync = MagicMock()
    handler_async = AsyncMock()
    handler_bad = MagicMock(side_effect=RuntimeError("bad"))

    dim_manager.register_access_handler(handler_sync)
    dim_manager.register_access_handler(handler_async)
    dim_manager.register_access_handler(handler_bad)
    rid = await dim_manager.ingest_data(
        "config_data", {"k": "v"}, sensitivity=DataSensitivity.RESTRICTED
    )
    await dim_manager.retrieve_data(rid, user_id="u1")
    handler_sync.assert_called_once()
    handler_async.assert_awaited_once()
    handler_bad.assert_called_once()


def test_dim_statistics(dim_manager):
    stats = dim_manager.get_statistics()
    assert stats["total_sources"] == 4
    assert stats["total_policies"] == 5


def test_dim_factory():
    from core.data_integration_manager import get_data_integration_manager

    mgr = get_data_integration_manager({"storage_dir": "/tmp/dim_test"})
    assert mgr is not None


# ---------------------------------------------------------------------------
# core.backup
# ---------------------------------------------------------------------------
class _FakeSubprocess:
    TimeoutExpired = subprocess.TimeoutExpired

    @staticmethod
    def run(*args, **kwargs):
        return SimpleNamespace(returncode=0, stdout="[]", stderr="")


class _FailingSubprocess:
    TimeoutExpired = subprocess.TimeoutExpired

    @staticmethod
    def run(*args, **kwargs):
        return SimpleNamespace(returncode=1, stdout="", stderr="wal-g failed")


class _TimeoutSubprocess:
    TimeoutExpired = subprocess.TimeoutExpired

    @staticmethod
    def run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0] if args else "cmd", timeout=1)


class _ExplodingSubprocess:
    TimeoutExpired = subprocess.TimeoutExpired

    @staticmethod
    def run(*args, **kwargs):
        raise RuntimeError("boom")


class _ListDeleteSubprocess:
    TimeoutExpired = subprocess.TimeoutExpired

    @staticmethod
    def run(*args, **kwargs):
        if args and args[0][1] == "backup-list":
            old = [
                {
                    "backup_name": "old_backup",
                    "start_time": (
                        datetime.datetime.now() - datetime.timedelta(days=8)
                    ).isoformat(),
                }
            ]
            return SimpleNamespace(returncode=0, stdout=json.dumps(old), stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")


@pytest.fixture
def backup_manager(monkeypatch):
    monkeypatch.setattr("core.backup.subprocess_runner", _FakeSubprocess())
    monkeypatch.setattr("core.task_scheduler.scheduler", MagicMock())

    import core.backup as backup

    manager = backup.BackupManager(
        {
            "wal_g_path": "wal-g",
            "s3_bucket": "bucket",
            "retention_days": 7,
        }
    )
    return manager


@pytest.mark.asyncio
async def test_backup_initialize_and_create(backup_manager, monkeypatch):
    import core.backup as backup

    assert backup_manager.initialize() is True
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 1234)
    info = await backup_manager.create_backup(backup.BackupType.FULL)
    assert info.status == backup.BackupStatus.COMPLETED
    assert info.size_bytes == 1234


@pytest.mark.asyncio
async def test_backup_create_incremental(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 1)
    info = await backup_manager.create_backup(backup.BackupType.INCREMENTAL)
    assert info.status == backup.BackupStatus.COMPLETED


@pytest.mark.asyncio
async def test_backup_create_differential(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 1)
    info = await backup_manager.create_backup(backup.BackupType.DIFFERENTIAL)
    assert info.status == backup.BackupStatus.COMPLETED


@pytest.mark.asyncio
async def test_backup_create_failures(backup_manager, monkeypatch):
    import core.backup as backup

    with pytest.raises(RuntimeError):
        await backup_manager.create_backup(backup.BackupType.FULL)

    backup_manager.initialize()
    monkeypatch.setattr(backup, "subprocess_runner", _FailingSubprocess())
    info = await backup_manager.create_backup(backup.BackupType.FULL)
    assert info.status == backup.BackupStatus.FAILED

    monkeypatch.setattr(backup, "subprocess_runner", _TimeoutSubprocess())
    info = await backup_manager.create_backup(backup.BackupType.FULL)
    assert info.status == backup.BackupStatus.FAILED
    assert "timeout" in info.error.lower()


@pytest.mark.asyncio
async def test_backup_restore(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 0)
    info = await backup_manager.create_backup(backup.BackupType.FULL)

    result = await backup_manager.restore_backup(info.backup_id)  # noqa: F841  # Variable for test verification
    assert result is True

    not_found = await backup_manager.restore_backup("missing")
    assert not_found is False

    info.status = backup.BackupStatus.FAILED
    not_completed = await backup_manager.restore_backup(info.backup_id)
    assert not_completed is False

    monkeypatch.setattr(backup, "subprocess_runner", _FailingSubprocess())
    fail = await backup_manager.restore_backup(info.backup_id)
    assert fail is False

    monkeypatch.setattr(backup, "subprocess_runner", _TimeoutSubprocess())
    timeout = await backup_manager.restore_backup(info.backup_id)
    assert timeout is False


@pytest.mark.asyncio
async def test_backup_list_and_cleanup(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 0)
    await backup_manager.create_backup(backup.BackupType.FULL)

    backups = await backup_manager.list_backups()
    assert isinstance(backups, list)

    monkeypatch.setattr(
        backup,
        "subprocess_runner",
        _FakeSubprocess(),
    )
    count = await backup_manager.cleanup_old_backups()
    assert count >= 0


def test_backup_status_and_schedule(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    backup_manager._backups["b1"] = backup.BackupInfo(
        backup_id="b1",
        backup_type=backup.BackupType.FULL,
        status=backup.BackupStatus.COMPLETED,
        start_time=datetime.datetime.now(),
    )
    status = backup_manager.get_backup_status("b1")
    assert status is not None
    assert status["backup_id"] == "b1"
    assert len(backup_manager.get_all_backup_statuses()) == 1

    assert backup_manager.schedule_backup(backup.BackupType.FULL, "0 2 * * *") is True

    class BadScheduler:
        def schedule_task(self, *a, **k):
            raise RuntimeError("fail")

    monkeypatch.setattr("core.task_scheduler.scheduler", BadScheduler())
    assert backup_manager.schedule_backup(backup.BackupType.FULL) is False


def test_backup_status_not_found(backup_manager):
    assert backup_manager.get_backup_status("missing") is None


@pytest.mark.asyncio
async def test_backup_initialize_exception(monkeypatch):
    import core.backup as backup

    monkeypatch.setattr("core.backup.subprocess_runner", _ExplodingSubprocess())
    manager = backup.BackupManager({"wal_g_path": "wal-g"})
    assert manager.initialize() is False


@pytest.mark.asyncio
async def test_backup_create_generic_exception(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 0)
    monkeypatch.setattr("core.backup.subprocess_runner", _ExplodingSubprocess())
    info = await backup_manager.create_backup(backup.BackupType.FULL)
    assert info.status == backup.BackupStatus.FAILED
    assert "boom" in info.error


@pytest.mark.asyncio
async def test_backup_restore_target_and_exception(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr(backup.BackupManager, "_get_backup_size", lambda self, bid: 0)
    info = await backup_manager.create_backup(backup.BackupType.FULL)

    target = datetime.datetime.now() - datetime.timedelta(hours=1)
    ok = await backup_manager.restore_backup(info.backup_id, target_time=target)
    assert ok is True

    monkeypatch.setattr("core.backup.subprocess_runner", _ExplodingSubprocess())
    fail = await backup_manager.restore_backup(info.backup_id)
    assert fail is False


@pytest.mark.asyncio
async def test_backup_list_exception(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr("core.backup.subprocess_runner", _ExplodingSubprocess())
    backups = await backup_manager.list_backups()
    assert backups == []


@pytest.mark.asyncio
async def test_backup_cleanup_deletes_old(backup_manager, monkeypatch):
    import core.backup as backup

    backup_manager.initialize()
    monkeypatch.setattr("core.backup.subprocess_runner", _ListDeleteSubprocess())
    count = await backup_manager.cleanup_old_backups()
    assert count == 1


def test_backup_create_manager_exception(monkeypatch):
    import core.backup as backup

    class BadManager:
        def __init__(self, *a, **k):
            raise RuntimeError("init boom")

    monkeypatch.setattr(backup, "BackupManager", BadManager)
    mgr = backup.create_backup_manager({"wal_g_path": "wal-g"})
    assert mgr is None


@pytest.mark.asyncio
async def test_backup_get_size_with_boto3(monkeypatch):
    import core.backup as backup

    fake_client = MagicMock()
    fake_client.get_paginator.return_value.paginate.return_value = [
        {"Contents": [{"Size": 100}, {"Size": 200}]}
    ]
    fake_boto3 = SimpleNamespace(client=lambda *a, **k: fake_client)
    monkeypatch.setitem(sys.modules, "boto3", fake_boto3)

    manager = backup.BackupManager({"wal_g_path": "wal-g", "s3_bucket": "b"})
    size = manager._get_backup_size("bid/")
    assert size == 300


def test_backup_create_manager(monkeypatch):
    import core.backup as backup

    monkeypatch.setattr(backup, "subprocess_runner", _FakeSubprocess())
    mgr = backup.create_backup_manager({"wal_g_path": "wal-g"})
    assert mgr is not None

    monkeypatch.setattr(backup, "subprocess_runner", _FailingSubprocess())
    mgr2 = backup.create_backup_manager({"wal_g_path": "wal-g"})
    assert mgr2 is None
