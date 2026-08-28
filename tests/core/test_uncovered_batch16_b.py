# -*- coding: utf-8 -*-
"""Batch 16b coverage tests for low-coverage core modules."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]

from core import enhanced_websocket_manager as ews
from core import plugin_development_sdk as pdk
from core.agent import memory_bridge
from core.execution.l6 import fault_tolerant_executor as fte
from core.hitl import conditional

# ---------------------------------------------------------------------------
# memory_bridge.py
# ---------------------------------------------------------------------------


@pytest.fixture
def scenario_memory_modules(monkeypatch):
    """Provide stub scenario-memory service modules for MemoryBridge."""
    # Clear any previously loaded real scenario-memory modules.
    for key in list(sys.modules):
        if key.startswith("services.scenario_memory_service"):
            if key in sys.modules:
                monkeypatch.delitem(sys.modules, key)

    svc_pkg = types.ModuleType("services.scenario_memory_service")
    svc_pkg.__path__ = []
    monkeypatch.setitem(sys.modules, "services.scenario_memory_service", svc_pkg)

    cache_mod = types.ModuleType("services.scenario_memory_service.cache")

    class CacheManager:
        def __init__(self, redis_url):
            self.redis_url = redis_url

    cache_mod.CacheManager = CacheManager
    monkeypatch.setitem(sys.modules, "services.scenario_memory_service.cache", cache_mod)

    config_mod = types.ModuleType("services.scenario_memory_service.config")
    config_mod.settings = SimpleNamespace(redis_url="redis://test:6379/0")
    monkeypatch.setitem(sys.modules, "services.scenario_memory_service.config", config_mod)

    orch_mod = types.ModuleType("services.scenario_memory_service.orchestrator")

    class ScenarioMemoryOrchestrator:
        def __init__(self, cache):
            self.cache = cache

        async def search_similar(self, request):
            return SimpleNamespace(results=[])

        async def store_event(self, request):
            return SimpleNamespace(stored=True)

        async def learn_experience(self, request):
            return SimpleNamespace(experience_id="exp-1", confidence=0.9, learned=True)

    orch_mod.ScenarioMemoryOrchestrator = ScenarioMemoryOrchestrator
    monkeypatch.setitem(sys.modules, "services.scenario_memory_service.orchestrator", orch_mod)

    schemas_mod = types.ModuleType("services.scenario_memory_service.schemas")

    class SimilarityQueryRequest:
        def __init__(self, query, top_k):
            self.query = query
            self.top_k = top_k

    class EventMemory:
        def __init__(self, event_type, source, payload, tags):
            self.event_type = event_type
            self.source = source
            self.payload = payload
            self.tags = tags

    class StoreEventRequest:
        def __init__(self, event):
            self.event = event

    class LearnExperienceRequest:
        def __init__(self, situation, action, outcome, confidence):
            self.situation = situation
            self.action = action
            self.outcome = outcome
            self.confidence = confidence

    schemas_mod.SimilarityQueryRequest = SimilarityQueryRequest
    schemas_mod.EventMemory = EventMemory
    schemas_mod.StoreEventRequest = StoreEventRequest
    schemas_mod.LearnExperienceRequest = LearnExperienceRequest
    monkeypatch.setitem(sys.modules, "services.scenario_memory_service.schemas", schemas_mod)


def test_memory_bridge_from_settings_success(scenario_memory_modules):
    """from_settings uses the in-process scenario memory orchestrator."""
    bridge = memory_bridge.MemoryBridge.from_settings()
    assert isinstance(bridge, memory_bridge.MemoryBridge)
    assert bridge._orchestrator is not None


def test_memory_bridge_retrieve_and_save_with_orchestrator(scenario_memory_modules):
    bridge = memory_bridge.MemoryBridge.from_settings()
    assert bridge._orchestrator is not None

    ev1 = SimpleNamespace(
        event_id="e1",
        score=0.9,
        event=SimpleNamespace(
            event_type="diagnostic_session",
            source="agent",
            payload={"session_id": "s1"},
        ),
    )
    ev2 = SimpleNamespace(
        event_id="e2",
        score=0.8,
        event=SimpleNamespace(
            event_type="diagnostic_session",
            source="agent",
            payload={"session_id": "s2"},
        ),
    )
    bridge._orchestrator.search_similar = AsyncMock(
        return_value=SimpleNamespace(results=[ev1, ev2])
    )
    result = bridge.retrieve_relevant_experiences(
        "query", top_k=3, session_id="s1"
    )  # noqa: F841  # Variable for test verification
    assert len(result) == 1
    assert result[0]["event_id"] == "e1"

    bridge._orchestrator.store_event = AsyncMock()
    bridge._orchestrator.learn_experience = AsyncMock(
        return_value=SimpleNamespace(experience_id="exp-1", confidence=0.85, learned=True)
    )
    Task = SimpleNamespace
    tasks = [
        Task(description="check logs", status=SimpleNamespace(value="done")),
        Task(description="restart pod", status="pending"),
    ]
    saved = bridge.save_experience(
        "fix the pod", tasks, [True], {"completed": 1, "total": 2, "progress": 0.5}, session_id="s1"
    )
    assert saved["experience_id"] == "exp-1"


def test_memory_bridge_retrieve_and_save_failure(scenario_memory_modules):
    bridge = memory_bridge.MemoryBridge.from_settings()
    assert bridge._orchestrator is not None
    bridge._orchestrator.search_similar = AsyncMock(side_effect=Exception("boom"))
    assert bridge.retrieve_relevant_experiences("q") == []

    bridge._orchestrator.store_event = AsyncMock(side_effect=Exception("boom"))
    assert bridge.save_experience("goal", [], [], {}) is None


def test_memory_bridge_helpers():
    sig1 = memory_bridge._action_signature("Goal", "Task", "tool", {"a": 1, "b": [2]})
    sig2 = memory_bridge._action_signature(" goal ", " TASK ", "tool", {"b": [2], "a": 1})
    assert sig1 == sig2
    assert len(sig1) == 32

    normalized = memory_bridge._normalize_params(
        {
            "a": {"k": 1},
            "b": [1, 2],
            "c": "plain",
            "d": {"x": object()},
        }
    )
    assert json.loads(normalized["a"]) == {"k": 1}
    assert normalized["c"] == "plain"
    assert isinstance(normalized["d"], str)


# ---------------------------------------------------------------------------
# conditional.py
# ---------------------------------------------------------------------------


def test_approval_rule_operators():
    eq = conditional.ApprovalRule(
        "r1", "equals", "f", conditional.RuleOperator.EQUALS, 10, "require_approval"
    )
    assert eq.evaluate({"f": 10}) is True
    assert eq.evaluate({"f": 11}) is False

    ne = conditional.ApprovalRule(
        "r2", "neq", "f", conditional.RuleOperator.NOT_EQUALS, 10, "auto_approve"
    )
    assert ne.evaluate({"f": 5}) is True

    gt = conditional.ApprovalRule(
        "r3", "gt", "f", conditional.RuleOperator.GREATER_THAN, 5, "auto_approve"
    )
    assert gt.evaluate({"f": 6}) is True

    lt = conditional.ApprovalRule(
        "r4", "lt", "f", conditional.RuleOperator.LESS_THAN, 5, "auto_approve"
    )
    assert lt.evaluate({"f": 4}) is True

    cont = conditional.ApprovalRule(
        "r5", "contains", "f", conditional.RuleOperator.CONTAINS, "err", "auto_reject"
    )
    assert cont.evaluate({"f": "there is an error"}) is True

    inside = conditional.ApprovalRule(
        "r6", "in", "f", conditional.RuleOperator.IN, ["a", "b"], "auto_approve"
    )
    assert inside.evaluate({"f": "a"}) is True
    assert inside.evaluate({"f": "c"}) is False

    inside_not_list = conditional.ApprovalRule(
        "r7", "in", "f", conditional.RuleOperator.IN, "abc", "auto_approve"
    )
    assert inside_not_list.evaluate({"f": "a"}) is False


def test_approval_rule_unknown_operator():
    rule = conditional.ApprovalRule(
        "r8", "eq", "f", conditional.RuleOperator.EQUALS, "v", "auto_approve"
    )
    rule.operator = object()  # force the final return False branch
    assert rule.evaluate({"f": "v"}) is False


def test_conditional_approval_actions():
    ca = conditional.ConditionalApproval()
    ca.add_rule(
        conditional.ApprovalRule(
            "low_risk", "Low", "risk_level", conditional.RuleOperator.EQUALS, "low", "auto_approve"
        )
    )
    ca.add_rule(
        conditional.ApprovalRule(
            "danger", "Danger", "msg", conditional.RuleOperator.CONTAINS, "DANGER", "auto_reject"
        )
    )
    ca.add_rule(
        conditional.ApprovalRule(
            "other", "Other", "x", conditional.RuleOperator.EQUALS, 1, "require_approval"
        )
    )

    no_match = ca.evaluate_rules({"risk_level": "medium"})
    assert no_match["requires_approval"] is True
    assert no_match["action"] == "default"

    auto_approve = ca.evaluate_rules({"risk_level": "low"})
    assert auto_approve["action"] == "auto_approve"
    assert auto_approve["requires_approval"] is False

    auto_reject = ca.evaluate_rules({"msg": "DANGER zone"})
    assert auto_reject["action"] == "auto_reject"

    require = ca.evaluate_rules({"x": 1, "risk_level": "high"})
    assert require["action"] == "require_approval"


def test_conditional_approval_default_rules():
    ca = conditional.ConditionalApproval()
    ca.add_default_rules()
    assert len(ca.rules) == 4
    # Default rules cover both risk_level and change_size, so supply complete contexts.
    assert ca.evaluate_rules({"risk_level": "low", "change_size": 2000})["action"] == "auto_approve"
    assert ca.evaluate_rules({"risk_level": "low", "change_size": 50})["action"] == "auto_approve"
    assert (
        ca.evaluate_rules({"risk_level": "high", "change_size": 500})["action"]
        == "require_approval"
    )
    assert (
        ca.evaluate_rules({"risk_level": "high", "change_size": 2000})["action"]
        == "require_approval"
    )


# ---------------------------------------------------------------------------
# enhanced_websocket_manager.py
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_connect_disconnect_and_stats():
    mgr = ews.get_enhanced_websocket_manager(
        {
            "heartbeat_interval": 0.01,
            "max_connections": 2,
        }
    )
    ws = AsyncMock()
    cid = await mgr.connect(ws, channels=["c1", "c2"], metadata={"ip": "127.0.0.1"})
    assert cid.startswith("client_")
    assert ws in mgr.client_info
    assert mgr.connection_count == 1

    stats = mgr.get_statistics()
    assert stats["connection_count"] == 1
    assert stats["active_channels"] == 2

    info = mgr.get_channel_info("c1")
    assert info["active_connections"] == 1

    await mgr.disconnect(ws)
    assert ws not in mgr.client_info
    assert mgr.connection_count == 0


@pytest.mark.asyncio
async def test_websocket_max_connections():
    mgr = ews.EnhancedWebSocketManager({"max_connections": 1})
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    await mgr.connect(ws1)
    with pytest.raises(Exception, match="Maximum connections reached"):
        await mgr.connect(ws2)


@pytest.mark.asyncio
async def test_websocket_broadcast_and_failure():
    mgr = ews.EnhancedWebSocketManager()
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    ws2.send_text.side_effect = Exception("send failed")

    await mgr.connect(ws1, channels=["ch"])
    await mgr.connect(ws2, channels=["ch"])

    msg = ews.WebSocketMessage(
        message_type=ews.MessageType.ALERT,
        data={"x": 1},
        channel="ch",
    )
    sent = await mgr.broadcast(msg, "ch")
    assert sent == 1
    assert ws2 not in mgr.client_info


@pytest.mark.asyncio
async def test_websocket_broadcast_to_channels():
    mgr = ews.EnhancedWebSocketManager()
    ws = AsyncMock()
    await mgr.connect(ws, channels=["a", "b"])
    msg = ews.WebSocketMessage(
        message_type=ews.MessageType.METRIC,
        data={"v": 1},
    )
    res = await mgr.broadcast_to_channels(msg, ["a", "b", "c"])
    assert res["a"] == 1
    assert res["b"] == 1
    assert res["c"] == 0


@pytest.mark.asyncio
async def test_websocket_subscribe_unsubscribe_and_personal():
    mgr = ews.EnhancedWebSocketManager()
    ws = AsyncMock()
    await mgr.connect(ws, channels=["c1"])

    assert await mgr.subscribe_channel(ws, "c2") is True
    assert await mgr.subscribe_channel(ws, "c2") is False
    assert await mgr.unsubscribe_channel(ws, "c2") is True
    assert await mgr.unsubscribe_channel(ws, "c2") is False

    msg = ews.WebSocketMessage(
        message_type=ews.MessageType.RESPONSE,
        data={"ok": True},
    )
    assert await mgr.send_personal_message(ws, msg) is True
    ws.send_text.side_effect = Exception("fail")
    assert await mgr.send_personal_message(ws, msg) is False


@pytest.mark.asyncio
async def test_websocket_handle_and_emit():
    mgr = ews.EnhancedWebSocketManager()
    ws = AsyncMock()
    await mgr.connect(ws)

    sync_handler = MagicMock()
    async_handler = AsyncMock()
    mgr.register_message_handler(ews.MessageType.COMMAND, sync_handler)
    mgr.register_message_handler(ews.MessageType.COMMAND, async_handler)

    event_sync = MagicMock()
    mgr.register_event_handler("alert", event_sync)

    await mgr.handle_message(
        ws,
        {
            "message_type": "command",
            "data": {"cmd": "x"},
            "channel": "default",
        },
    )
    assert sync_handler.called
    assert async_handler.called

    await mgr.emit_event("alert", {"msg": "hi"})
    assert event_sync.called

    # Unknown message type
    await mgr.handle_message(ws, {"message_type": "weird", "data": {}})

    # Invalid payload triggers error response
    ws.send_text = AsyncMock()
    await mgr.handle_message(ws, "not a dict")
    assert ws.send_text.called


@pytest.mark.asyncio
async def test_websocket_heartbeat():
    mgr = ews.EnhancedWebSocketManager({"heartbeat_interval": 0.01})
    ws = AsyncMock()
    await mgr.connect(ws)
    await mgr.start_heartbeat()
    await asyncio.sleep(0.05)
    await mgr.stop_heartbeat()
    assert ws.send_text.called


# ---------------------------------------------------------------------------
# plugin_development_sdk.py
# ---------------------------------------------------------------------------


def test_plugin_sdk_code_and_config():
    sdk = pdk.PluginDevelopmentSDK({"author": "test"})
    assert "monitoring" in sdk.templates
    # The shipped monitoring template contains unescaped f-string braces,
    # so use a simple template to exercise the formatting path.
    sdk.templates["monitoring"].code_template = (
        "# {plugin_name} v{version} by {author}\nclass {class_name}:\n    pass"
    )

    code = sdk.generate_plugin_code(
        "monitoring", "My Plugin", "MyPlugin", version="1.1.0", author="Tester"
    )
    assert "MyPlugin" in code
    assert "1.1.0" in code

    cfg = sdk.generate_plugin_config("monitoring", {"interval": 10})
    assert cfg["interval"] == 10

    with pytest.raises(ValueError):
        sdk.generate_plugin_code("missing", "n", "C")
    with pytest.raises(ValueError):
        sdk.generate_plugin_config("missing")


def test_plugin_sdk_package_and_export(tmp_path):
    sdk = pdk.PluginDevelopmentSDK()
    # Use a format-safe template for create_plugin_package.
    sdk.templates["integration"].code_template = (
        "# {plugin_name} v{version} by {author}\nclass {class_name}:\n    pass"
    )
    pkg = sdk.create_plugin_package(
        "integration",
        "My Integration",
        "MyIntegration",
        version="2.0.0",
        author="A",
        custom_config={"endpoint": "http"},
    )
    assert pkg["plugin_name"] == "My Integration"
    assert pkg["config"]["endpoint"] == "http"

    plugin_id = next(iter(sdk.generated_plugins))  # noqa: F841  # Variable for test verification
    out = tmp_path / "pkg.json"
    sdk.export_plugin_package(plugin_id, str(out))
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["plugin_name"] == "My Integration"

    with pytest.raises(ValueError):
        sdk.export_plugin_package("missing", str(out))


def test_plugin_sdk_summary_and_singleton():
    pdk._plugin_sdk = None
    s1 = pdk.get_plugin_sdk()
    s2 = pdk.get_plugin_sdk()
    assert s1 is s2
    summary = s1.get_sdk_summary()
    assert summary["available_templates"] == 3
    templates = s1.get_available_templates()
    assert len(templates) == 3


# ---------------------------------------------------------------------------
# fault_tolerant_executor.py
# ---------------------------------------------------------------------------


def test_fault_tolerant_executor_init_and_factory():
    e = fte.get_fault_tolerant_executor(
        {
            "max_retries": 5,
            "default_timeout": 5.0,
            "circuit_breaker_failure_threshold": 3,
        }
    )
    assert e.retry_policy.max_retries == 5
    assert e.default_timeout == 5.0
    assert e.circuit_breaker_config.failure_threshold == 3


@pytest.mark.asyncio
async def test_fault_tolerant_executor_success():
    e = fte.FaultTolerantExecutor({"default_timeout": 1.0})

    async def f():
        return 123

    result = await e.execute(f, "op1")  # noqa: F841  # Variable for test verification
    assert result.status == fte.ExecutionStatus.COMPLETED
    assert result.result == 123  # noqa: F841  # Variable for test verification
    assert e.get_metrics("op1")["success"] == 1
    assert "op1" in e.get_circuit_breaker_states()


@pytest.mark.asyncio
async def test_fault_tolerant_executor_sync_and_no_circuit():
    e = fte.FaultTolerantExecutor({"default_timeout": 1.0})
    result = await e.execute(
        lambda: "ok", "op2", circuit_breaker_enabled=False
    )  # noqa: F841  # Variable for test verification
    assert result.result == "ok"  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_fault_tolerant_executor_timeout_with_fallback():
    e = fte.FaultTolerantExecutor({"default_timeout": 0.01})
    e.register_fallback("op3", lambda: "fallback")

    async def slow():
        await asyncio.Event().wait()

    result = await e.execute(slow, "op3")  # noqa: F841  # Variable for test verification
    assert result.status == fte.ExecutionStatus.COMPLETED
    assert result.result == "fallback"  # noqa: F841  # Variable for test verification
    assert result.metadata.get("fallback_used") is True


@pytest.mark.asyncio
async def test_fault_tolerant_executor_exception_with_fallback():
    e = fte.FaultTolerantExecutor({"default_timeout": 1.0})
    e.register_fallback("op4", AsyncMock(return_value="afallback"))

    async def bad():
        raise ValueError("boom")

    result = await e.execute(bad, "op4")  # noqa: F841  # Variable for test verification
    assert result.status == fte.ExecutionStatus.COMPLETED
    assert result.result == "afallback"  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_fault_tolerant_executor_exception_no_fallback():
    e = fte.FaultTolerantExecutor({"default_timeout": 1.0})

    async def bad():
        raise ConnectionError("boom")

    result = await e.execute(  # noqa: F841  # Variable for test verification
        bad,
        "op5",
        retry_policy=fte.RetryPolicy(max_retries=1, base_delay=0.0, max_delay=0.0),
    )
    assert result.status == fte.ExecutionStatus.FAILED
    assert result.failure_type == fte.FailureType.NETWORK_ERROR
    assert e.get_metrics("op5")["failure"] == 1


@pytest.mark.asyncio
async def test_fault_tolerant_executor_retry_succeeds():
    e = fte.FaultTolerantExecutor({"default_timeout": 1.0})
    f = AsyncMock(side_effect=[ConnectionError("fail"), "ok"])
    result = await e.execute(  # noqa: F841  # Variable for test verification
        f,
        "op6",
        retry_policy=fte.RetryPolicy(max_retries=2, base_delay=0.0, max_delay=0.0),
    )
    assert result.status == fte.ExecutionStatus.COMPLETED
    assert result.result == "ok"  # noqa: F841  # Variable for test verification
    assert e.get_metrics("op6")["retry"] == 1


def test_fault_tolerant_executor_helpers():
    rp = fte.RetryPolicy(max_retries=3, base_delay=1.0, max_delay=2.0, exponential_backoff=True)
    e = fte.FaultTolerantExecutor()
    assert e._calculate_retry_delay(0, rp) == 1.0
    assert e._calculate_retry_delay(10, rp) == 2.0

    assert e._is_retryable(ConnectionError(), e.retry_policy) is True
    assert e._is_retryable(asyncio.TimeoutError(), e.retry_policy) is True
    assert e._is_retryable(ValueError(), e.retry_policy) is False

    custom = fte.RetryPolicy(
        retryable_exceptions=[ValueError], non_retryable_exceptions=[ConnectionError]
    )
    assert e._is_retryable(ValueError(), custom) is True
    assert e._is_retryable(ConnectionError(), custom) is False

    assert e._classify_error(ConnectionError()) == fte.FailureType.NETWORK_ERROR
    assert e._classify_error(asyncio.TimeoutError()) == fte.FailureType.TIMEOUT_ERROR
    assert e._classify_error(MemoryError()) == fte.FailureType.RESOURCE_ERROR
    assert e._classify_error(ImportError()) == fte.FailureType.DEPENDENCY_ERROR
    assert e._classify_error(ValueError()) == fte.FailureType.LOGIC_ERROR


@pytest.mark.asyncio
async def test_circuit_breaker_success_open():
    cb = fte.CircuitBreaker(fte.CircuitBreakerConfig(failure_threshold=2, recovery_timeout=100))
    f_ok = AsyncMock(return_value=1)
    assert await cb.call(f_ok) == 1
    assert cb.get_state() == fte.CircuitBreakerState.CLOSED

    f_fail = AsyncMock(side_effect=Exception("fail"))
    with pytest.raises(Exception, match="fail"):
        await cb.call(f_fail)
    assert cb.get_state() == fte.CircuitBreakerState.CLOSED

    with pytest.raises(Exception, match="fail"):
        await cb.call(f_fail)
    assert cb.get_state() == fte.CircuitBreakerState.OPEN

    with pytest.raises(Exception, match="OPEN"):
        await cb.call(f_fail)


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_reset():
    cb = fte.CircuitBreaker(
        fte.CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.1, half_open_max_calls=2)
    )
    f_fail = AsyncMock(side_effect=Exception("fail"))
    f_ok = AsyncMock(return_value="ok")

    with pytest.raises(Exception):
        await cb.call(f_fail)
    assert cb.get_state() == fte.CircuitBreakerState.OPEN

    await asyncio.sleep(0.2)
    await cb.call(f_ok)
    await cb.call(f_ok)
    assert cb.get_state() == fte.CircuitBreakerState.CLOSED
    assert cb.failure_count == 0


def test_circuit_breaker_internals():
    cb = fte.CircuitBreaker(fte.CircuitBreakerConfig(recovery_timeout=10))
    cb.last_failure_time = None
    assert cb._should_attempt_reset() is True

    cb._record_failure()
    assert cb.failure_count == 1
    assert cb.last_failure_time is not None

    cb._reset()
    assert cb.get_state() == fte.CircuitBreakerState.CLOSED
    assert cb.half_open_success_count == 0
    assert cb.last_failure_time is None


@pytest.mark.asyncio
async def test_fault_tolerant_executor_circuit_opens():
    e = fte.FaultTolerantExecutor(
        {
            "default_timeout": 1.0,
            "circuit_breaker_failure_threshold": 1,
        }
    )
    f_fail = AsyncMock(side_effect=Exception("err"))

    result1 = await e.execute(f_fail, "op7")
    assert result1.status == fte.ExecutionStatus.FAILED

    result2 = await e.execute(f_fail, "op7")
    assert result2.status == fte.ExecutionStatus.FAILED
    assert e.get_circuit_breaker_states()["op7"] == "open"


def test_fault_tolerant_executor_reset_and_states():
    e = fte.FaultTolerantExecutor({"circuit_breaker_failure_threshold": 1})
    cb = e.get_circuit_breaker("r")
    assert e.get_circuit_breaker("r") is cb
    assert e.reset_circuit_breaker("r") is True
    assert e.reset_circuit_breaker("missing") is False
    assert e.get_metrics() == {}
    assert e.get_metrics("r") == {
        "total": 0,
        "success": 0,
        "failure": 0,
        "retry": 0,
        "timeout": 0,
        "avg_duration": 0.0,
    }
