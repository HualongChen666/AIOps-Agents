# -*- coding: utf-8 -*-
"""Functional coverage tests for batch20b core modules."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup
from fastapi import Request

import core.windows_collector as win_col
from core.db_optimization import (
    PERFORMANCE_INDEXES,
    _IndexSpec,
    analyze_query_performance,
    clear_slow_queries,
    configure_db_optimization,
    create_performance_indexes,
    get_connection_pool_config,
    get_connection_pool_statistics,
    get_db_optimization_config,
    get_missing_indexes_suggestions,
    get_performance_summary,
    get_query_cache_config,
    get_query_cache_statistics,
    get_slow_queries,
    is_db_optimization_enabled,
    optimize_database_configuration,
    record_connection_pool_usage,
    record_query_cache_hit,
    record_query_cache_miss,
    record_slow_query,
    reset_query_cache,
    reset_query_cache_statistics,
    run_comprehensive_optimization,
    suggest_optimizations,
    update_database_statistics,
    update_query_cache_config,
    validate_sql_identifier,
    validate_sql_query_structure,
    validate_table_name,
)
from core.db_read_write_router import (
    QueryType,
    ReadWriteRouter,
    ReplicaState,
    get_read_write_router,
)
from core.error_logging import fastapi_handlers as fhandlers
from core.error_recovery import core as ercore
from core.exceptions import (
    AIModelException,
    AuthenticationException,
    AuthorizationException,
    DatabaseException,
    ExternalServiceException,
    NetworkException,
    PermissionDeniedException,
    QuotaExceededException,
    ResourceNotFoundException,
    SystemFatalException,
    ValidationException,
    VersionMismatchException,
)

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.error_logging.fastapi_handlers
# ---------------------------------------------------------------------------
@pytest.fixture
def patch_log_exception(monkeypatch):
    monkeypatch.setattr("core.error_logging.logger.log_exception", MagicMock())


def _run_handler(handler, exc):
    return asyncio.run(handler(MagicMock(), exc))


def test_validation_exception_handler(patch_log_exception):
    exc = ValidationException("validation failed", field="x", value=1)
    resp = _run_handler(fhandlers.validation_exception_handler, exc)
    assert resp.status_code == 400
    assert json.loads(resp.body)["error_type"] == "ValidationException"


def test_resource_not_found_exception_handler(patch_log_exception):
    exc = ResourceNotFoundException("missing", resource_type="user", resource_id=1)
    resp = _run_handler(fhandlers.resource_not_found_exception_handler, exc)
    assert resp.status_code == 404
    assert json.loads(resp.body)["error_type"] == "ResourceNotFoundException"


def test_authentication_exception_handler(patch_log_exception):
    exc = AuthenticationException("auth failed", token="abc1234567890xyz")
    resp = _run_handler(fhandlers.authentication_exception_handler, exc)
    assert resp.status_code == 401
    assert json.loads(resp.body)["error_type"] == "AuthenticationException"


def test_authorization_exception_handler(patch_log_exception):
    exc = AuthorizationException("forbidden", required_role="admin", current_role="user")
    resp = _run_handler(fhandlers.authorization_exception_handler, exc)
    assert resp.status_code == 403
    assert json.loads(resp.body)["error_type"] == "AuthorizationException"


def test_permission_denied_exception_handler(patch_log_exception):
    exc = PermissionDeniedException("denied", resource="file", action="delete")
    resp = _run_handler(fhandlers.permission_denied_exception_handler, exc)
    assert resp.status_code == 403
    assert json.loads(resp.body)["error_type"] == "PermissionDeniedException"


def test_database_exception_handler(patch_log_exception):
    exc = DatabaseException("db down", host="db", port=5432, database="aiops")
    resp = _run_handler(fhandlers.database_exception_handler, exc)
    assert resp.status_code == 500
    assert json.loads(resp.body)["error_type"] == "DatabaseException"


def test_network_exception_handler(patch_log_exception):
    exc = NetworkException("timeout", url="http://api", timeout=5.0)
    resp = _run_handler(fhandlers.network_exception_handler, exc)
    assert resp.status_code == 502
    assert json.loads(resp.body)["error_type"] == "NetworkException"


def test_external_service_exception_handler(patch_log_exception):
    exc = ExternalServiceException("service error", service_name="x", service_url="http://x")
    resp = _run_handler(fhandlers.external_service_exception_handler, exc)
    assert resp.status_code == 502
    assert json.loads(resp.body)["error_type"] == "ExternalServiceException"


def test_ai_model_exception_handler(patch_log_exception):
    exc = AIModelException("model fail", model_name="gpt", error_type="timeout")
    resp = _run_handler(fhandlers.ai_model_exception_handler, exc)
    assert resp.status_code == 500
    assert json.loads(resp.body)["error_type"] == "AIModelException"


def test_quota_exceeded_exception_handler(patch_log_exception):
    exc = QuotaExceededException("over quota", quota_type="api", current_usage=120, quota_limit=100)
    resp = _run_handler(fhandlers.quota_exceeded_exception_handler, exc)
    assert resp.status_code == 429
    assert json.loads(resp.body)["error_type"] == "QuotaExceededException"


def test_version_mismatch_exception_handler(patch_log_exception):
    exc = VersionMismatchException(
        "mismatch", current_version="1", required_version="2", component="x"
    )
    resp = _run_handler(fhandlers.version_mismatch_exception_handler, exc)
    assert resp.status_code == 409
    assert json.loads(resp.body)["error_type"] == "VersionMismatchException"


def test_system_fatal_exception_handler(patch_log_exception):
    exc = SystemFatalException("fatal", service="core", error_code_detail="x")
    resp = _run_handler(fhandlers.system_fatal_exception_handler, exc)
    assert resp.status_code == 503
    assert json.loads(resp.body)["error_type"] == "SystemFatalException"


def test_generic_exception_handler(patch_log_exception):
    exc = Exception("plain boom")
    resp = _run_handler(fhandlers.generic_exception_handler, exc)
    assert resp.status_code == 500
    body = json.loads(resp.body)
    assert body["error_type"] == "InternalServerError"
    assert body["error_code"] == "01_15_0003"


def test_setup_exception_handlers():
    app = MagicMock()
    fhandlers.setup_exception_handlers(app)
    assert app.add_exception_handler.call_count >= 12


# ---------------------------------------------------------------------------
# core.windows_collector
# ---------------------------------------------------------------------------
def _make_winrm_module():
    sess = MagicMock()
    sess.open_shell.return_value = "shell-1"
    sess.run_command.return_value = "cmd-1"
    sess.get_command_output.return_value = (b"12.5\n", b"", 0)
    sess.cleanup_command.return_value = None
    sess.close_shell.return_value = None
    mod = ModuleType("winrm")
    mod.Protocol = MagicMock(return_value=sess)
    return mod


def test_execute_winrm_success(monkeypatch):
    mod = _make_winrm_module()
    monkeypatch.setitem(sys.modules, "winrm", mod)
    out = asyncio.run(
        win_col._execute_winrm(
            {"ip": "10.0.0.1", "port": 5986, "user": "u", "password": "p"},
            "Get-Date",
        )
    )
    assert out.strip() == "12.5"
    assert mod.Protocol.called


def test_execute_winrm_missing_library(monkeypatch):
    monkeypatch.delitem(sys.modules, "winrm", raising=False)
    with pytest.raises(ModuleNotFoundError):
        asyncio.run(
            win_col._execute_winrm(
                {"ip": "10.0.0.1", "user": "u", "password": "p"},
                "cmd",
            )
        )


def test_execute_winrm_cert_validation_ignore(monkeypatch):
    mod = _make_winrm_module()
    monkeypatch.setitem(sys.modules, "winrm", mod)
    monkeypatch.setattr(win_col, "WINRM_CERT_VALIDATION", "ignore")
    asyncio.run(
        win_col._execute_winrm(
            {"ip": "10.0.0.1", "user": "u", "password": "p"},
            "cmd",
        )
    )
    assert mod.Protocol.called


def test_collect_windows_host_success(monkeypatch):
    monkeypatch.setattr(win_col, "_execute_winrm", AsyncMock(return_value="10.0"))
    result = asyncio.run(  # noqa: F841  # Variable for test verification
        win_col.collect_windows_host(
            {"ip": "10.0.0.1", "name": "host1", "user": "u", "password": "p"}
        )
    )
    assert result["host"] == "host1"
    assert result["cpu_percent"] == 10.0
    assert result["memory_free_mb"] == 10.0 / 1024
    assert "timestamp" in result


def test_collect_windows_host_failure(monkeypatch):
    monkeypatch.setattr(
        win_col, "_execute_winrm", AsyncMock(side_effect=RuntimeError("winrm down"))
    )
    result = asyncio.run(  # noqa: F841  # Variable for test verification
        win_col.collect_windows_host(
            {"ip": "10.0.0.1", "name": "host2", "user": "u", "password": "p"}
        )
    )
    assert result["host"] == "host2"
    assert "error" in result


def test_collect_all_windows(monkeypatch):
    monkeypatch.setattr(win_col, "_execute_winrm", AsyncMock(return_value="5.0"))
    monkeypatch.setattr(
        win_col,
        "WIN_HOSTS",
        [
            {"ip": "1.1.1.1", "name": "h1", "user": "u", "password": "p"},
            {"ip": "2.2.2.2", "name": "h2", "user": "u", "password": "p"},
        ],
    )
    results = asyncio.run(win_col.collect_all_windows())
    assert len(results) == 2
    assert results[0]["host"] == "h1"
    assert results[1]["host"] == "h2"


# ---------------------------------------------------------------------------
# core.db_optimization
# ---------------------------------------------------------------------------
def _make_session_maker(results):
    class _Session:
        def __init__(self, results):
            self._results = iter(results)
            self.commit = AsyncMock()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def execute(self, *args, **kwargs):
            try:
                val = next(self._results)
            except StopIteration:
                raise RuntimeError("no more mock results")
            if isinstance(val, Exception):
                raise val
            return val

    class _Maker:
        async def __aenter__(self):
            return _Session(results)

        async def __aexit__(self, exc_type, exc, tb):
            return None

    return MagicMock(return_value=_Maker())


def test_validate_sql_identifier():
    assert validate_sql_identifier("alerts") == "alerts"
    with pytest.raises(ValueError):
        validate_sql_identifier(123)
    with pytest.raises(ValueError):
        validate_sql_identifier("")
    with pytest.raises(ValueError):
        validate_sql_identifier("drop")
    with pytest.raises(ValueError):
        validate_sql_identifier("123abc")
    with pytest.raises(ValueError):
        validate_sql_identifier("a;b")
    with pytest.raises(ValueError):
        validate_sql_identifier("a..b")
    with pytest.raises(ValueError):
        validate_sql_identifier('a"b')
    with pytest.raises(ValueError):
        validate_sql_identifier("a" + "x" * 200)


def test_validate_table_name():
    assert validate_table_name("alerts") == "alerts"
    with pytest.raises(ValueError):
        validate_table_name("unknown_table")
    with pytest.raises(ValueError):
        validate_table_name("select")


def test_validate_sql_query_structure():
    assert validate_sql_query_structure("SELECT * FROM alerts", ["SELECT"]) is True
    with pytest.raises(ValueError):
        validate_sql_query_structure("DROP TABLE alerts", ["SELECT"])
    with pytest.raises(ValueError):
        validate_sql_query_structure("; DROP TABLE alerts", ["SELECT"])
    with pytest.raises(ValueError):
        validate_sql_query_structure("SELECT * FROM t WHERE 1 OR 1 = 1", ["SELECT"])
    with pytest.raises(ValueError):
        validate_sql_query_structure(123)


def test_create_performance_indexes_sqlite_skip(monkeypatch):
    monkeypatch.setenv("USE_SQLITE", "true")
    result = asyncio.run(
        create_performance_indexes()
    )  # noqa: F841  # Variable for test verification
    assert result["skipped"] is True


def test_create_performance_indexes(monkeypatch):
    monkeypatch.setenv("USE_SQLITE", "false")
    indexes = [
        _IndexSpec("idx_new", "alerts", ["detected_at"]),
        _IndexSpec("idx_exists", "alerts", ["status"]),
        _IndexSpec(None, "alerts", ["host"]),
        _IndexSpec("idx_fail", "alerts", ["host"]),
        _IndexSpec("idx_bad", "", ["host"]),
    ]
    monkeypatch.setattr("core.db_optimization.PERFORMANCE_INDEXES", indexes)

    check_new = MagicMock(fetchone=MagicMock(return_value=None))
    check_exists = MagicMock(fetchone=MagicMock(return_value=("row",)))
    check_fail = MagicMock(fetchone=MagicMock(return_value=None))
    check_bad = MagicMock(fetchone=MagicMock(return_value=None))
    create_ok = MagicMock()
    results = [
        check_new,
        create_ok,
        check_exists,
        check_fail,
        RuntimeError("create fail"),
        check_bad,
    ]
    monkeypatch.setattr("core.db_optimization.AsyncSessionLocal", _make_session_maker(results))

    result = asyncio.run(
        create_performance_indexes()
    )  # noqa: F841  # Variable for test verification
    assert result["created"] == 1
    assert result["already_exists"] == 1
    assert result["failed"] == 1


def test_create_performance_indexes_outer_error(monkeypatch):
    monkeypatch.setenv("USE_SQLITE", "false")
    monkeypatch.setattr(
        "core.db_optimization.AsyncSessionLocal",
        MagicMock(side_effect=RuntimeError("db connect failed")),
    )
    result = asyncio.run(
        create_performance_indexes()
    )  # noqa: F841  # Variable for test verification
    assert "error" in result


def test_analyze_query_performance(monkeypatch):
    rows = [
        ["SELECT * FROM t", 100, 5000.0, 10.0, 20.0, 2.0],
        ["SELECT id FROM t", 50, 1000.0, 2.0, 5.0, 0.5],
    ]
    result = MagicMock(
        fetchall=MagicMock(return_value=rows)
    )  # noqa: F841  # Variable for test verification
    monkeypatch.setattr("core.db_optimization.AsyncSessionLocal", _make_session_maker([result]))
    analysis = asyncio.run(analyze_query_performance())
    assert analysis["total_analyzed"] == 2
    assert len(analysis["very_slow_queries"]) == 1
    assert len(analysis["slow_queries"]) == 1


def test_update_database_statistics(monkeypatch):
    monkeypatch.setattr(
        "core.db_optimization.AsyncSessionLocal",
        _make_session_maker([MagicMock() for _ in range(4)]),
    )
    result = asyncio.run(
        update_database_statistics()
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "completed"
    assert "results" in result


def test_get_missing_indexes_suggestions(monkeypatch):
    rows = [
        ["public", "alerts", "detected_at", 0, 0, 0],
    ]
    result = MagicMock(
        fetchall=MagicMock(return_value=rows)
    )  # noqa: F841  # Variable for test verification
    monkeypatch.setattr("core.db_optimization.AsyncSessionLocal", _make_session_maker([result]))
    suggestions = asyncio.run(get_missing_indexes_suggestions())
    assert isinstance(suggestions, list)
    assert suggestions[0]["recommendation"]


def test_optimize_database_configuration(monkeypatch):
    monkeypatch.setattr(
        "core.db_optimization.AsyncSessionLocal",
        _make_session_maker([MagicMock(), MagicMock(), MagicMock()]),
    )
    result = asyncio.run(
        optimize_database_configuration()
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert len(result["optimizations_applied"]) == 3


def test_run_comprehensive_optimization(monkeypatch):
    monkeypatch.setattr(
        "core.db_optimization.create_performance_indexes",
        AsyncMock(return_value={"created": 1}),
    )
    monkeypatch.setattr(
        "core.db_optimization.update_database_statistics",
        AsyncMock(return_value={"status": "completed"}),
    )
    monkeypatch.setattr(
        "core.db_optimization.analyze_query_performance",
        AsyncMock(return_value={"slow_queries": []}),
    )
    monkeypatch.setattr(
        "core.db_optimization.get_missing_indexes_suggestions",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "core.db_optimization.optimize_database_configuration",
        AsyncMock(return_value={"status": "success"}),
    )
    result = asyncio.run(
        run_comprehensive_optimization()
    )  # noqa: F841  # Variable for test verification
    assert "steps" in result
    assert "create_indexes" in result["steps"]


def test_db_optimization_state_components():
    reset_query_cache()
    clear_slow_queries()
    configure_db_optimization({"enabled": True, "level": "advanced"})
    assert is_db_optimization_enabled() is True
    assert get_db_optimization_config()["level"] == "advanced"

    record_query_cache_hit("q1")
    assert get_query_cache_statistics()["hits"] == 1
    record_query_cache_miss("q2")
    assert get_query_cache_statistics()["misses"] == 1
    update_query_cache_config({"enabled": True, "size": 500})
    assert get_query_cache_config()["size"] == 500

    record_connection_pool_usage(20, 5)
    stats = get_connection_pool_statistics()
    assert stats["active_connections"] == 5
    assert get_connection_pool_config()["active"] == 5

    record_slow_query("SELECT * FROM alerts", 9999.0)
    assert len(get_slow_queries()) == 1
    summary = get_performance_summary()
    assert "cache_hit_rate" in summary

    reset_query_cache_statistics()
    assert get_query_cache_statistics()["hits"] == 0
    assert get_query_cache_statistics()["misses"] == 0

    suggestions = suggest_optimizations()
    assert isinstance(suggestions, list)


# ---------------------------------------------------------------------------
# core.error_recovery.core
# ---------------------------------------------------------------------------
def test_circuit_breaker_success_and_open():
    cb = ercore.CircuitBreaker(
        ercore.CircuitBreakerConfig(failure_threshold=2, recovery_timeout=60)
    )

    async def ok():
        return "ok"

    async def fail():
        raise ValueError("fail")

    assert asyncio.run(cb.call(ok)) == "ok"
    with pytest.raises(ValueError):
        asyncio.run(cb.call(fail))
    with pytest.raises(ValueError):
        asyncio.run(cb.call(fail))
    assert cb.get_state() == ercore.CircuitState.OPEN
    with pytest.raises(ercore.CircuitBreakerOpenError):
        asyncio.run(cb.call(ok))


def test_circuit_breaker_half_open_reset():
    cb = ercore.CircuitBreaker(
        ercore.CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.01)
    )

    async def fail():
        raise RuntimeError("fail")

    async def ok():
        return "ok"

    with pytest.raises(RuntimeError):
        asyncio.run(cb.call(fail))
    assert cb.get_state() == ercore.CircuitState.OPEN
    time.sleep(0.05)
    assert asyncio.run(cb.call(ok)) == "ok"
    assert cb.get_state() == ercore.CircuitState.CLOSED
    assert cb.get_stats()["failure_count"] == 0


def test_retry_policy():
    cfg = ercore.RetryConfig(
        max_attempts=3,
        base_delay=0.01,
        max_delay=0.1,
        exponential_base=2.0,
        jitter=False,
        retryable_exceptions=[ValueError],
    )
    policy = ercore.RetryPolicy(cfg)
    assert policy.should_retry(ValueError("x"), 1) is True
    assert policy.should_retry(ValueError("x"), 3) is False
    assert policy.calculate_delay(1) == 0.01
    assert 0 < policy.calculate_delay(10) <= 0.1


def test_retry_with_policy_success():
    async def ok():
        return "done"

    cfg = ercore.RetryConfig(max_attempts=2, base_delay=0.001, jitter=False)
    assert asyncio.run(ercore.retry_with_policy(ok, cfg)) == "done"


def test_retry_with_policy_failure():
    calls = [0]

    async def fail():
        calls[0] += 1
        raise ValueError("x")

    cfg = ercore.RetryConfig(
        max_attempts=2, base_delay=0.001, jitter=False, retryable_exceptions=[ValueError]
    )
    with pytest.raises(ValueError):
        asyncio.run(ercore.retry_with_policy(fail, cfg))
    assert calls[0] == 2


def test_retry_decorator():
    calls = [0]
    cfg = ercore.RetryConfig(
        max_attempts=2, base_delay=0.001, jitter=False, retryable_exceptions=[ValueError]
    )

    @ercore.retry_decorator(cfg)
    async def may_fail():
        calls[0] += 1
        if calls[0] < 2:
            raise ValueError("x")
        return "ok"

    assert asyncio.run(may_fail()) == "ok"
    assert calls[0] == 2


def test_error_recovery_manager():
    manager = ercore.ErrorRecoveryManager()

    async def strategy(error):
        return True

    manager.register_recovery_strategy("RuntimeError", strategy)
    manager.register_circuit_breaker("db", ercore.CircuitBreakerConfig(failure_threshold=1))

    async def ok():
        return "ok"

    assert asyncio.run(manager.execute_with_circuit_breaker("missing", ok)) == "ok"
    assert asyncio.run(manager.execute_with_circuit_breaker("db", ok)) == "ok"
    assert asyncio.run(manager.attempt_recovery(RuntimeError("x"))) is True
    assert asyncio.run(manager.attempt_recovery(ValueError("x"))) is False

    stats = manager.get_circuit_breaker_stats("db")
    assert stats is not None
    assert stats["state"] == "closed"
    assert manager.get_circuit_breaker_stats("missing") is None


def test_setup_error_recovery():
    result = asyncio.run(
        ercore.setup_error_recovery()
    )  # noqa: F841  # Variable for test verification
    assert result["status"] == "success"
    assert "database" in result["circuit_breakers"]
    assert "DatabaseError" in result["recovery_strategies"]


# ---------------------------------------------------------------------------
# core.db_read_write_router
# ---------------------------------------------------------------------------
def test_router_factory():
    router = get_read_write_router({"primary_host": "p"})
    assert isinstance(router, ReadWriteRouter)


def test_classify_query():
    router = ReadWriteRouter({})
    assert router.classify_query("SELECT * FROM t") == QueryType.READ
    assert router.classify_query("WITH t AS (SELECT 1) SELECT * FROM t") == QueryType.READ
    assert router.classify_query("SHOW tables") == QueryType.READ
    assert router.classify_query("INSERT INTO t VALUES (1)") == QueryType.WRITE
    assert router.classify_query("UPDATE t SET x=1") == QueryType.WRITE
    assert router.classify_query("DELETE FROM t") == QueryType.WRITE
    assert router.classify_query("BEGIN TRANSACTION") == QueryType.TRANSACTION
    assert router.classify_query("COMMIT") == QueryType.TRANSACTION
    assert router.classify_query("CREATE TABLE t (x INT)") == QueryType.SCHEMA
    assert router.classify_query("UNKNOWN") == QueryType.READ


def test_route_query_write_to_primary():
    router = ReadWriteRouter(
        {
            "primary_host": "p",
            "primary_port": 5432,
            "replicas": [{"host": "r1", "port": 5433}],
        }
    )
    decision = router.route_query("INSERT INTO t VALUES (1)")
    assert decision.target_host == "p"
    assert decision.query_type == QueryType.WRITE
    assert decision.replica_used is False


def test_route_query_read_to_replica():
    router = ReadWriteRouter(
        {
            "primary_host": "p",
            "primary_port": 5432,
            "replicas": [{"host": "r1", "port": 5433}],
            "load_balancing_method": "round_robin",
        }
    )
    d1 = router.route_query("SELECT * FROM t")
    assert d1.replica_used is True
    assert d1.target_host == "r1"


def test_route_query_splitting_disabled_and_unavailable():
    router1 = ReadWriteRouter(
        {
            "primary_host": "p",
            "primary_port": 5432,
            "read_write_splitting_enabled": False,
            "replicas": [{"host": "r1", "port": 5433}],
        }
    )
    d = router1.route_query("SELECT 1")
    assert d.replica_used is False
    assert d.target_host == "p"

    router2 = ReadWriteRouter(
        {
            "primary_host": "p",
            "primary_port": 5432,
            "replicas": [{"host": "r1", "port": 5433}],
            "lag_threshold": 0.1,
        }
    )
    router2.update_replica_state("replica_0", ReplicaState.UNHEALTHY, lag=10.0)
    d = router2.route_query("SELECT 1")
    assert d.replica_used is False
    assert d.target_host == "p"


def test_select_replica_methods():
    router_rr = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1"}, {"host": "r2"}],
            "load_balancing_method": "round_robin",
        }
    )
    hosts = {router_rr._select_replica().host for _ in range(2)}
    assert hosts == {"r1", "r2"}

    router_lag = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1"}, {"host": "r2"}],
            "load_balancing_method": "least_lag",
        }
    )
    router_lag.replicas["replica_0"].lag = 10.0
    router_lag.replicas["replica_1"].lag = 0.1
    assert router_lag._select_replica().host == "r2"

    router_conn = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1"}, {"host": "r2"}],
            "load_balancing_method": "least_connections",
        }
    )
    router_conn.replicas["replica_0"].connections = 100
    router_conn.replicas["replica_1"].connections = 1
    assert router_conn._select_replica().host == "r2"

    router_rand = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1"}],
            "load_balancing_method": "random",
        }
    )
    assert router_rand._select_replica().host == "r1"
    assert ReadWriteRouter({"primary_host": "p"})._select_replica() is None


def test_update_replica_state_and_stats():
    router = ReadWriteRouter(
        {
            "primary_host": "p",
            "primary_port": 5432,
            "replicas": [{"host": "r1", "port": 5433}],
        }
    )
    router.update_replica_state("replica_0", ReplicaState.MAINTENANCE, lag=1.0, connections=3)
    r = router.replicas["replica_0"]
    assert r.state == ReplicaState.MAINTENANCE
    assert r.lag == 1.0
    assert r.connections == 3
    assert r.load_score > 0
    stats = router.get_routing_stats()
    assert stats["total_queries"] == 0
    assert "replicas" in stats


def test_enable_read_write_splitting():
    router = ReadWriteRouter({"primary_host": "p"})
    assert router.read_write_splitting_enabled is True
    router.enable_read_write_splitting(False)
    assert router.read_write_splitting_enabled is False


def test_check_replicas_health(monkeypatch):
    router = ReadWriteRouter({"primary_host": "p", "replicas": [{"host": "r1", "port": 5433}]})
    asyncio.run(router._check_all_replicas_health())
    assert router.replicas["replica_0"].state == ReplicaState.HEALTHY

    monkeypatch.setattr(router, "_check_replica_health", AsyncMock(return_value=False))
    asyncio.run(router._check_all_replicas_health())
    assert router.replicas["replica_0"].state == ReplicaState.UNHEALTHY

    monkeypatch.setattr(router, "_check_replica_health", AsyncMock(side_effect=RuntimeError("x")))
    asyncio.run(router._check_all_replicas_health())
    assert router.replicas["replica_0"].state == ReplicaState.UNHEALTHY


def test_health_check_loop_cancelled(monkeypatch):
    router = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1", "port": 5433}],
            "health_check_enabled": True,
            "health_check_interval": 0.001,
        }
    )
    monkeypatch.setattr(router, "_check_all_replicas_health", AsyncMock())

    async def cancel_sleep(*args, **kwargs):
        raise asyncio.CancelledError()

    monkeypatch.setattr("core.db_read_write_router.asyncio.sleep", cancel_sleep)
    asyncio.run(router.health_check_loop())
    assert router._check_all_replicas_health.called


def test_health_check_loop_disabled():
    router = ReadWriteRouter(
        {
            "primary_host": "p",
            "replicas": [{"host": "r1", "port": 5433}],
            "health_check_enabled": False,
        }
    )
    asyncio.run(router.health_check_loop())
    assert router.health_check_enabled is False
