# -*- coding: utf-8 -*-
"""Batch 29a: targeted coverage for low-coverage core modules."""

import asyncio
import re
import socket
import time
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.core]

import core.ai.llm_router.load_balancer as load_balancer
import core.ai.token_budget as token_budget
import core.observability_query as oq
from core.agent.tools import (
    Tool,
    ToolCategory,
    ToolExecutor,
    ToolRegistry,
    ToolSelector,
)
from core.audit_logger import (
    get_trace_id,
    log_alert_generated,
    log_audit_event,
    log_data_access,
    log_login_event,
    log_logout_event,
    log_permission_change,
    log_repair_executed,
    log_token_refresh,
    set_trace_id,
)


# ----------------------------------------------------------------------
# core/observability_query.py
# ----------------------------------------------------------------------

def test_query_cache_eviction_and_expiry(monkeypatch):
    cache = oq.QueryCache(ttl=60.0, max_size=2)

    # cover set() deleting an existing key (line 109) and capacity eviction (111-112)
    cache.set("a", 1)
    cache.set("a", 2)
    cache.set("b", 3)
    cache.set("c", 4)  # evicts oldest (a)
    assert "a" not in cache._store or len(cache._order) <= 2

    # cover expired get (102-103)
    cache._store["b"] = (99, 0.0)
    monkeypatch.setattr(oq.time, "monotonic", lambda: 1000.0)
    value, ok = cache.get("b")
    assert not ok
    assert value is None


@pytest.mark.asyncio
async def test_cached_query_stale_fallback_and_ttl():
    cache = oq.QueryCache()
    cache.get = MagicMock(side_effect=[(None, False), ({"result": 1}, True)])

    async def fail1():
        raise RuntimeError("boom")

    out1 = await oq.cached_query(cache, "k1", fail1(), ttl=5.0)
    assert out1["_stale"] is True

    cache2 = oq.QueryCache()
    cache2.get = MagicMock(side_effect=[(None, False), ([1, 2, 3], True)])

    async def fail2():
        raise RuntimeError("boom")

    out2 = await oq.cached_query(cache2, "k2", fail2())
    assert out2["_stale"] is True
    assert out2["_partial"] == [1, 2, 3]

    # no stale cache -> re-raise
    cache3 = oq.QueryCache()

    async def fail3():
        raise RuntimeError("no stale")

    with pytest.raises(RuntimeError, match="no stale"):
        await oq.cached_query(cache3, "missing", fail3())


def test_validate_promql_and_logql_errors():
    with pytest.raises(ValueError, match="non-empty"):
        oq.validate_promql("")
    with pytest.raises(ValueError, match="too long"):
        oq.validate_promql("a" * 2001)
    with pytest.raises(ValueError, match="control"):
        oq.validate_promql("up\x01")
    with pytest.raises(ValueError, match="comment"):
        oq.validate_promql("up;")
    with pytest.raises(ValueError, match="SQL"):
        oq.validate_promql("drop table x")
    with pytest.raises(ValueError, match="invalid characters"):
        oq.validate_promql("up?")

    with pytest.raises(ValueError, match="unbalanced"):
        oq.validate_logql("{foo=bar")
    with pytest.raises(ValueError, match="invalid characters"):
        oq.validate_logql("up @")

    with pytest.raises(ValueError, match="non-empty"):
        oq.validate_tempoql("")


def test_validate_es_query_string_errors():
    with pytest.raises(ValueError, match="must be a string"):
        oq.validate_es_query_string(None)
    with pytest.raises(ValueError, match="too long"):
        oq.validate_es_query_string("x" * 2001)
    with pytest.raises(ValueError, match="control"):
        oq.validate_es_query_string("foo\x01")
    with pytest.raises(ValueError, match="disallowed characters"):
        oq.validate_es_query_string("foo ~bar")
    with pytest.raises(ValueError, match="SQL"):
        oq.validate_es_query_string("foo delete")
    with pytest.raises(ValueError, match="invalid characters"):
        oq.validate_es_query_string("foo@bar")


def test_validate_clickhouse_identifier_and_metric():
    with pytest.raises(ValueError, match="required"):
        oq.validate_clickhouse_identifier("")
    with pytest.raises(ValueError, match="required"):
        oq.validate_clickhouse_identifier(None)
    with pytest.raises(ValueError, match="Invalid ClickHouse identifier"):
        oq.validate_clickhouse_identifier("123table")

    with pytest.raises(ValueError, match="Metric name required"):
        oq.validate_clickhouse_metric_name("")
    with pytest.raises(ValueError, match="Invalid metric name"):
        oq.validate_clickhouse_metric_name("1metric")


def test_redact_and_prepare_branches(monkeypatch):
    # redact_text on non-str returns as-is
    assert oq.redact_text(123) == 123

    # _redact_recursive sensitive key redaction
    assert oq._redact_recursive({"my_password": "secret"})["my_password"] == "<REDACTED>"
    # nested list/dict
    assert oq._redact_recursive([{"email": "a@b.com"}])[0]["email"] == "<EMAIL_REDACTED>"
    # non-str, non-dict, non-list value passes through
    assert oq._redact_recursive({"count": 42})["count"] == 42

    # approx_token_count fallback when json.dumps fails
    def bad_dumps(*args, **kwargs):
        raise TypeError("nope")

    monkeypatch.setattr(oq.json, "dumps", bad_dumps)
    assert oq.approx_token_count(object()) >= 1
    monkeypatch.undo()

    # prepare_for_llm forced to shrink 10 times without early break
    monkeypatch.setattr(oq, "approx_token_count", lambda x: 100000)
    huge = {"items": ["x" * 1000 for _ in range(100)]}
    result = oq.prepare_for_llm(huge, max_tokens=1, max_items=1)
    assert result["_llm_meta"]["truncated"] is True

    # dict truncation marker
    truncated = oq._truncate({"a": 1, "b": 2, "c": 3}, max_items=2, max_string_chars=10)
    assert "..." in truncated

    # list sampling when larger than max_items
    big_list = list(range(20))
    sampled = oq._truncate(big_list, max_items=5, max_string_chars=10)
    assert len(sampled) <= 5

    # string truncation
    assert oq._truncate("hello world", max_items=5, max_string_chars=5).endswith("...<TRUNCATED>")


def test_time_helpers():
    # align with naive end datetime
    start, end = oq.align_time_window(datetime(2024, 1, 1), duration_seconds=60)
    assert end.tzinfo is not None

    # parse empty string returns default 60s
    assert oq.parse_duration_to_seconds("") == 60.0

    # invalid duration raises
    with pytest.raises(ValueError):
        oq.parse_duration_to_seconds("abc")

    # limit_range_samples: step <= 0 coerced
    now = datetime.now(timezone.utc)
    assert oq.limit_range_samples(now, now + timedelta(minutes=1), -5) == 60.0

    # zero span
    assert oq.limit_range_samples(now, now, 15.0) == 15.0

    # too many samples coarsened
    start = now - timedelta(days=10)
    coarse = oq.limit_range_samples(start, now, 15.0, max_samples=100)
    assert coarse > 15.0


def test_make_cache_key_and_semaphore():
    k1 = oq.make_cache_key("q", 1, {"a": 1})
    k2 = oq.make_cache_key("q", 1, {"a": 1})
    assert k1 == k2
    assert isinstance(k1, str)

    oq._query_semaphore = None
    sem = oq.get_query_semaphore(max_concurrent=5)
    assert isinstance(sem, asyncio.Semaphore)


# ----------------------------------------------------------------------
# core/ai/llm_router/load_balancer.py
# ----------------------------------------------------------------------

def test_circuit_breaker_half_open_and_recovery():
    cb = load_balancer.CircuitBreaker(
        failure_threshold=3, recovery_timeout=0.1, half_open_max_calls=2
    )

    # move to HALF_OPEN and recover to CLOSED
    cb.state = load_balancer.CircuitState.HALF_OPEN
    cb.half_open_calls = 1
    cb.record_success()
    assert cb.state == load_balancer.CircuitState.CLOSED
    assert cb.half_open_calls == 0

    # OPEN -> recovery timeout passed -> HALF_OPEN (covers 99-102)
    cb.state = load_balancer.CircuitState.OPEN
    cb.last_failure_time = time.time() - 10
    assert cb.can_request() is True
    assert cb.state == load_balancer.CircuitState.HALF_OPEN

    # HALF_OPEN with capacity (covers 105-108)
    cb.half_open_calls = 0
    cb.state = load_balancer.CircuitState.HALF_OPEN
    assert cb.can_request() is True
    cb.half_open_calls = 2
    assert cb.can_request() is False


def test_load_balancer_missing_branches():
    # init with missing / None model (covers 135)
    lb = load_balancer.LoadBalancer(
        [
            {"api_key": "x"},
            {"model": None},
            {"model": "m1", "cost_per_1k": 0.1},
            {"model": "m2", "cost_per_1k": 0.05},
        ]
    )
    assert set(lb.model_stats) == {"m1", "m2"}

    # explicit available_models bypasses the default list (covers 152->160)
    chosen = lb.select_model(available_models=["m1", "m2"], strategy="least_latency")
    assert chosen in ("m1", "m2")

    # least_requests strategy (covers 190-191)
    lb.record_request_start("m2")  # m2 now has more requests than m1
    assert lb.select_model(strategy="least_requests") == "m1"

    # record success with total_requests == 0 (covers 211)
    fresh = load_balancer.ModelStats("fresh")
    lb2 = load_balancer.LoadBalancer([{"model": "fresh"}])
    lb2.model_stats["fresh"] = fresh
    lb2.record_request_success("fresh", 0.123)
    assert fresh.total_requests == 1
    assert fresh.avg_latency == 0.123

    # get_model_stats missing returns None (covers 235)
    assert lb.get_model_stats("missing") is None


# ----------------------------------------------------------------------
# core/ai/token_budget.py
# ----------------------------------------------------------------------

def test_load_balancer_remaining_branches():
    cb = load_balancer.CircuitBreaker(failure_threshold=2, half_open_max_calls=2)
    cb.record_success()  # CLOSED state, cover record_success short path
    cb.record_failure()
    cb.record_failure()  # reaches threshold -> OPEN (76-81)
    assert cb.state == load_balancer.CircuitState.OPEN
    assert cb.get_state() == load_balancer.CircuitState.OPEN

    # request denied before recovery timeout (103)
    cb2 = load_balancer.CircuitBreaker(recovery_timeout=60)
    cb2.state = load_balancer.CircuitState.OPEN
    cb2.last_failure_time = time.time()
    assert cb2.can_request() is False

    lb = load_balancer.LoadBalancer([{"model": "m1"}, {"model": "m2"}])
    # round_robin selection (169 / 180-181)
    assert lb.select_model(strategy="round_robin") == "m1"
    # unknown strategy falls back to first available (175)
    assert lb.select_model(strategy="unknown") == "m1"

    # record_request_success when total_requests > 0 (210->212)
    lb.record_request_start("m2")
    lb.record_request_success("m2", 0.1)
    assert lb.model_stats["m2"].successful_requests == 1

    # record_request_failure and stats helpers (226-231 / 239 / 243)
    lb.record_request_failure("m1", "boom")
    assert lb.get_all_stats()["m1"].failed_requests == 1
    assert "m1" in lb.get_circuit_states()

    # all circuits open -> None (165-166)
    for m in lb.circuit_breakers.values():
        m.state = load_balancer.CircuitState.OPEN
        m.last_failure_time = time.time()
    assert lb.select_model() is None


def test_token_budget_missing_branches():
    # CJK heuristic path
    with pytest.MonkeyPatch().context() as m:
        m.setattr(token_budget, "TIKTOKEN_AVAILABLE", False)
        assert token_budget.estimate_tokens("中文") > 0
        # _heuristic_token_count with CJK
        assert token_budget.estimate_tokens("hello") > 0

    # ContextWindowExceededError attributes
    err = token_budget.ContextWindowExceededError("boom", 10, 5, 12)
    assert err.prompt_tokens == 10
    assert err.max_new_tokens == 5
    assert err.context_window == 12

    # select_model_that_fits returns None when nothing fits
    assert (
        token_budget.select_model_that_fits(
            prompt="x" * 10000,
            max_new_tokens=10,
            model_configs=[{"name": "tiny", "context_window": 5}],
        )
        is None
    )


def test_prompt_fits_and_budget():
    fits, prompt_tokens, total = token_budget.prompt_fits(
        prompt="hello world", max_new_tokens=10, context_window=100
    )
    assert fits is True
    assert prompt_tokens >= 1
    budget = token_budget.calculate_prompt_budget(100, 10, system_tokens=5)
    assert budget > 0


# ----------------------------------------------------------------------
# core/audit_logger.py
# ----------------------------------------------------------------------

def test_audit_logger_with_trace_and_helpers():
    set_trace_id("trace-123")
    assert get_trace_id() == "trace-123"

    # log_audit_event with trace in details (covers 66)
    log_audit_event("LOGIN", "admin", details={"ip": "127.0.0.1"})

    # all helper event types
    log_login_event("admin", "127.0.0.1")
    log_logout_event("admin")
    log_token_refresh("admin")
    log_repair_executed("admin", "script.sh", "host1", status="success")
    log_permission_change("admin", "user2", "read", "granted")
    log_permission_change("admin", "user2", "read", "revoked")
    log_alert_generated("cpu", "high")
    log_data_access("admin", "db", "read", "127.0.0.1")

    set_trace_id(None)


# ----------------------------------------------------------------------
# core/agent/tools.py
# ----------------------------------------------------------------------

def test_tool_validation_missing_branches(monkeypatch):
    def dummy_fn(target: str, duration: int = 60, command: str = "", notes: str = ""):
        return {"target": target, "duration": duration, "command": command, "notes": notes}

    tool = Tool(
        name="dummy",
        description="dummy tool",
        category=ToolCategory.ANALYSIS,
        function=dummy_fn,
        required_params=["target"],
        optional_params=["duration", "command", "notes"],
        parameters={"timeout": 30},
    )

    # missing required
    with pytest.raises(ValueError, match="Missing required"):
        tool.execute()

    # invalid timeout value
    with pytest.raises(ValueError, match="Invalid timeout"):
        tool.execute(target="x", timeout="abc")

    # disallowed parameter
    with pytest.raises(ValueError, match="not allowed"):
        tool.execute(target="x", extra="bad")

    # clamping ignores non-integer values
    clamped = tool._clamp_parameter_ranges({"duration": "not-int"})
    assert clamped["duration"] == "not-int"

    # empty name-pattern param
    with pytest.raises(ValueError, match="cannot be empty"):
        tool.execute(target="")

    # path traversal
    with pytest.raises(ValueError, match="path traversal"):
        tool.execute(target="../etc")

    # shell metacharacter
    with pytest.raises(ValueError, match="dangerous"):
        tool.execute(target="x; rm")

    # default strict whitelist rejects disallowed chars (e.g. € is outside allowed set)
    with pytest.raises(ValueError, match="disallowed characters"):
        tool.execute(target="x", notes="bad€")

    # high-risk command_guard blocks execution
    monkeypatch.setattr(
        "core.agent.tools.RiskLevel",
        SimpleNamespace(BLOCKED="blocked", HIGH="high"),
    )
    monkeypatch.setattr(
        "core.agent.tools._analyze_command",
        lambda cmd: {"risk_level": "high", "reason": "dangerous"},
    )
    with pytest.raises(ValueError, match="blocked"):
        tool.execute(target="x", command="rm -rf /")


def test_tool_registry_and_executor_missing_branches(monkeypatch):
    monkeypatch.setenv("AIOPS_TOOL_REGISTRATION_APPROVAL_REQUIRED", "true")
    reg = ToolRegistry(approval_required=True)

    tool = Tool(
        name="x",
        description="x",
        category=ToolCategory.ANALYSIS,
        function=lambda: None,
    )

    # request approval and register
    rid = reg.request_tool_approval("x", "me")
    assert rid.startswith("approval_x_")
    reg.approve_tool("x", "boss")
    reg.register(tool)
    assert reg.is_tool_approved("x")

    # unregister without approval first
    reg.approval_manager.revoke("x")
    with pytest.raises(PermissionError):
        reg.unregister("x")
    reg.unregister("x", approved_by="boss")

    # ToolSelector keyword branches
    selector = ToolSelector(reg)
    assert selector.select_tool("collect logs", {}) is not None
    assert selector.select_tool("scale service", {}) is not None
    assert selector.select_tool("check health", {}) is not None
    assert selector.select_tool("correlate alerts", {}) is not None
    assert selector.select_tool("unknown task", {}) is None
    assert selector.select_tools_for_chain(["collect logs", "unknown"], {}) != []

    # Executor _infer_parameters aliases
    executor = ToolExecutor(reg, default_timeout=10)
    params = executor._infer_parameters(
        Tool(
            name="i",
            description="i",
            category=ToolCategory.ANALYSIS,
            function=lambda target, service, alert_id, service_name: None,
            required_params=["target", "service", "alert_id", "service_name"],
            optional_params=["service_name"],
        ),
        {"service": "svc", "alert": {"id": "a1"}},
    )
    assert params["target"] == "svc"
    assert params["service"] == "svc"
    assert params["alert_id"] == "a1"
    assert params["service_name"] == "svc"


def test_default_tool_fallback_branches(monkeypatch):
    # Stub the observability client to avoid real HTTP / Prometheus calls
    fake_client = SimpleNamespace(
        _safe_label=lambda s: re.sub(r"[^A-Za-z0-9_.\-]", "_", s),
        get_prometheus_url=lambda: None,
        query_prometheus=lambda q: None,
        query_prometheus_range=lambda q, s, e, st: None,
        _extract_prom_scalar_value=lambda x: None,
        query_service_metrics=lambda s, h: {},
        query_network_metrics=lambda t: {"packet_loss_percent": None},
        query_change_events=lambda t, h: [],
        query_kubernetes_events=lambda ns, fs, limit: [],
        query_kubernetes_pod=lambda p, ns: {"available": False},
        query_kubernetes_node=lambda n: {"available": False},
    )
    monkeypatch.setattr("core.agent.tools.observability_client", fake_client)
    monkeypatch.setattr("shutil.which", lambda _name: None)

    reg = ToolRegistry(approval_required=False)
    executor = ToolExecutor(reg, default_timeout=5)

    # collect_metrics falls back to placeholders
    result = executor.execute_tool("collect_metrics", target="host")
    assert "note" in result

    # collect_service_metrics falls through no-prom/no-manager
    result = executor.execute_tool("collect_service_metrics", service_name="svc")
    assert result.get("note") or result.get("metrics") is not None

    # check_health socket path with connection failure
    def bad_conn(*args, **kwargs):
        raise OSError("down")

    monkeypatch.setattr(socket, "create_connection", bad_conn)
    result = executor.execute_tool("check_health", target="host:8080")
    assert result["healthy"] is False

    # restart_service and scale_service simulated because kubectl/systemctl not found
    result = executor.execute_tool("restart_service", service_name="nginx")
    assert result["status"] == "simulated"
    result = executor.execute_tool("scale_service", service_name="api", replicas=2)
    assert result["status"] == "simulated"
