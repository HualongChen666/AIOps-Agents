# -*- coding: utf-8 -*-
"""Functional coverage tests for core batch 11-c modules."""

import asyncio  # noqa: F401  # Imported for test setup
import datetime
import json  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup
import types
from unittest.mock import AsyncMock, MagicMock

import pytest  # noqa: F401  # Imported for test setup

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# core.sla_report_storage
# ---------------------------------------------------------------------------
@pytest.fixture
def sla_module(tmp_path, monkeypatch):
    import core.sla_report_storage as sla

    monkeypatch.setattr(sla, "_DATA_DIR", tmp_path)
    monkeypatch.setattr(sla, "_REPORTS_FILE", tmp_path / "sla_reports.json")
    return sla


def test_sla_save_and_list(sla_module):
    reports = [
        {"title": "Q1 SLA", "period": "2024-Q1", "compliance": 0.99},
        {"title": "Q2 SLA", "period": "2024-Q2", "compliance": 0.95},
        {"title": "Q1 SLA", "period": "2024-Q1", "compliance": 0.98},
    ]
    ids = sla_module.save_reports(reports)
    assert len(ids) == 3
    assert all(isinstance(i, str) and i for i in ids)

    all_reports = sla_module.list_reports()
    assert len(all_reports) == 3
    assert {r["period"] for r in all_reports} == {"2024-Q1", "2024-Q2"}

    q1 = sla_module.list_reports(period="2024-Q1")
    assert len(q1) == 2
    assert all(r["period"] == "2024-Q1" for r in q1)

    unknown = sla_module.list_reports(period="unknown")
    assert unknown == []


def test_sla_get_and_delete(sla_module):
    ids = sla_module.save_reports([{"title": "Delete Me", "period": "2024-Q3"}])
    report_id = ids[0]

    fetched = sla_module.get_report(report_id)
    assert fetched is not None
    assert fetched["id"] == report_id
    assert fetched["title"] == "Delete Me"

    assert sla_module.delete_report(report_id) is True
    assert sla_module.get_report(report_id) is None
    assert sla_module.delete_report(report_id) is False


def test_sla_prune_expired(sla_module):
    ids = sla_module.save_reports(
        [
            {"title": "Fresh", "period": "2024-Q1"},
            {"title": "Old", "period": "2023-Q4"},
        ]
    )
    assert len(ids) == 2

    # max_age_days=0 forces all non-future reports to be treated as expired
    removed = sla_module.prune_reports(max_age_days=0)
    assert removed == 2
    assert sla_module.list_reports() == []


def test_sla_load_missing_file(sla_module):
    assert sla_module.list_reports() == []


def test_sla_load_corrupt_json(sla_module):
    sla_module._REPORTS_FILE.write_text("not-json-at-all", encoding="utf-8")
    assert sla_module.list_reports() == []


def test_sla_invalid_and_missing_created_at(sla_module):
    broken = [
        {"id": "no-date", "title": "No date"},
        {"id": "bad-date", "title": "Bad date", "created_at": "not-a-timestamp"},
    ]
    sla_module._save({"reports": broken})
    removed = sla_module.prune_reports(max_age_days=30)
    assert removed == 2


# ---------------------------------------------------------------------------
# core.module_dependencies
# ---------------------------------------------------------------------------
def test_module_dependencies_validates():
    import core.module_dependencies as md

    assert md.validate_initialization_order() is True


def test_module_dependencies_invalid_order(monkeypatch):
    import core.module_dependencies as md

    bad_order = [
        "database",
        "ai_engine",
        "redis",
        "cache",
        "alert_engine",
        "metrics",
        "business_metrics",
    ]
    monkeypatch.setattr(md, "INITIALIZATION_ORDER", bad_order)
    with pytest.raises(ValueError, match="redis"):
        md.validate_initialization_order()


# ---------------------------------------------------------------------------
# core.ai.langgraph.nodes
# ---------------------------------------------------------------------------
class _TestNode:
    """Minimal concrete workflow node for node tests."""

    def __init__(self, name, result):
        self.name = name
        self.node_type = "test"
        self.config = {}
        self.result = result  # noqa: F841  # Variable for test verification

    async def execute(self, ctx):
        return self.result


@pytest.fixture
def mock_ai_engine(monkeypatch):
    fake = types.SimpleNamespace(
        analyze=AsyncMock(return_value="AI says: problem identified"),
    )
    monkeypatch.setitem(sys.modules, "core.ai_engine", fake)
    return fake


@pytest.mark.asyncio
async def test_llm_node_success(mock_ai_engine):
    from core.ai.langgraph.nodes import LLMNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = LLMNode(
        name="diagnose",
        prompt_template="Analyze {service} outage",
        system_prompt="You are an SRE",
        temperature=0.5,
        max_tokens=200,
    )
    ctx = WorkflowContext(state_data={"service": "payment"})
    result = await node.execute(ctx)  # noqa: F841  # Variable for test verification

    assert "AI says" in result
    assert mock_ai_engine.analyze.called
    args = mock_ai_engine.analyze.call_args.kwargs
    assert args["query"] == "Analyze payment outage"
    assert args["system_prompt"] == "You are an SRE"
    assert args["validate_json"] is False


@pytest.mark.asyncio
async def test_llm_node_falls_back_on_analyze_failure(monkeypatch):
    from core.ai.langgraph.nodes import LLMNode
    from core.ai.langgraph.workflow import WorkflowContext

    fake = types.SimpleNamespace(
        analyze=AsyncMock(side_effect=RuntimeError("LLM unreachable")),
    )
    monkeypatch.setitem(sys.modules, "core.ai_engine", fake)

    node = LLMNode(name="diagnose", prompt_template="Find {root}", system_prompt="")
    ctx = WorkflowContext(state_data={"root": "network"})
    result = await node.execute(ctx)  # noqa: F841  # Variable for test verification

    assert result.startswith("LLM response for:")
    assert "Find network" in result


@pytest.mark.asyncio
async def test_llm_node_execute_raises(monkeypatch):
    from core.ai.langgraph.nodes import LLMNode
    from core.ai.langgraph.workflow import WorkflowContext

    # remove the fake ai_engine so the fallback returns a string; we test the
    # outer execute() raising via an unformatted context
    monkeypatch.delitem(sys.modules, "core.ai_engine", raising=False)

    node = LLMNode(name="bad-ctx", prompt_template="Hello {name}")
    ctx = WorkflowContext(state_data=None)
    with pytest.raises(AttributeError):
        await node.execute(ctx)


@pytest.mark.asyncio
async def test_tool_node_execute():
    from core.ai.langgraph.nodes import ToolNode
    from core.ai.langgraph.workflow import WorkflowContext

    async def _tool(ctx, label=""):
        return f"ran {label} for {ctx.get('target')}"

    node = ToolNode("restart", _tool, tool_config={"label": "restart-service"})
    ctx = WorkflowContext(state_data={"target": "w3svc"})
    assert await node.execute(ctx) == "ran restart-service for w3svc"


@pytest.mark.asyncio
async def test_tool_node_exception():
    from core.ai.langgraph.nodes import ToolNode
    from core.ai.langgraph.workflow import WorkflowContext

    async def _boom(ctx):
        raise RuntimeError("tool failed")

    node = ToolNode("boom", _boom)
    with pytest.raises(RuntimeError, match="tool failed"):
        await node.execute(WorkflowContext())


@pytest.mark.asyncio
async def test_conditional_node_true_and_false():
    from core.ai.langgraph.nodes import ConditionalNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = ConditionalNode(
        name="gate",
        condition=lambda ctx: ctx.get("cpu", 0) > 80,
        true_branch="scale",
        false_branch="monitor",
    )
    assert await node.execute(WorkflowContext(state_data={"cpu": 95})) == "scale"
    assert await node.execute(WorkflowContext(state_data={"cpu": 40})) == "monitor"


@pytest.mark.asyncio
async def test_conditional_node_exception():
    from core.ai.langgraph.nodes import ConditionalNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = ConditionalNode(
        name="bad",
        condition=lambda ctx: 1 / 0,
        true_branch="a",
        false_branch="b",
    )
    with pytest.raises(ZeroDivisionError):
        await node.execute(WorkflowContext())


@pytest.mark.asyncio
async def test_parallel_node_success():
    from core.ai.langgraph.nodes import ParallelNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = ParallelNode(
        name="parallel",
        child_nodes=[_TestNode("fetch_metrics", {"cpu": 0.8}), _TestNode("fetch_logs", ["error"])],
    )
    result = await node.execute(WorkflowContext())  # noqa: F841  # Variable for test verification
    assert result == {"fetch_metrics": {"cpu": 0.8}, "fetch_logs": ["error"]}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_parallel_node_exception():
    from core.ai.langgraph.nodes import ParallelNode
    from core.ai.langgraph.workflow import WorkflowContext

    class _FailNode(_TestNode):
        async def execute(self, ctx):
            raise ValueError("child failed")

    node = ParallelNode(
        name="parallel",
        child_nodes=[_TestNode("ok", 1), _FailNode("bad", None)],
    )
    with pytest.raises(ValueError, match="child failed"):
        await node.execute(WorkflowContext())


@pytest.mark.asyncio
async def test_aggregator_node():
    from core.ai.langgraph.nodes import AggregatorNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = AggregatorNode("sum", lambda vals: sum(v for v in vals if v is not None), ["a", "b"])
    ctx = WorkflowContext(state_data={"a": 10, "b": 20})
    assert await node.execute(ctx) == 30


@pytest.mark.asyncio
async def test_aggregator_node_exception():
    from core.ai.langgraph.nodes import AggregatorNode
    from core.ai.langgraph.workflow import WorkflowContext

    node = AggregatorNode("bad", lambda vals: 1 / 0, ["a"])
    ctx = WorkflowContext(state_data={"a": 1})
    with pytest.raises(ZeroDivisionError):
        await node.execute(ctx)


# ---------------------------------------------------------------------------
# core.hitl.notification
# ---------------------------------------------------------------------------
@pytest.fixture
def hitl_module(monkeypatch):
    import core.hitl.notification as mod
    import core.notify_engine as ne

    # ensure the engine is seen as available and the channel senders are deterministic
    monkeypatch.setattr(mod, "NOTIFY_ENGINE_AVAILABLE", True)
    for name in (
        "_send_wecom",
        "_send_dingtalk",
        "_send_feishu",
        "send_slack_notification",
        "send_teams_notification",
        "send_email_notification",
    ):
        monkeypatch.setattr(mod, name, AsyncMock(return_value={"success": True}))

    # use a clean, isolated config for auto-configuration tests
    monkeypatch.setattr(ne, "NOTIFY_CONFIG", {})
    return mod


def _sample_request_data():
    return {
        "request_id": "REQ-2024-001",
        "title": "Restart payment service",
        "description": "Service is unstable after release",
        "context": {
            "risk_level": "high",
            "alert": "payment-p99 latency > 2s",
            "diagnosis": "latest release introduced a leak",
            "excluded_causes": ["network"],
            "hypothesis": "memory leak in worker",
            "confidence": 0.85,
            "executed_commands": ["collect metrics"],
            "dashboard_url": "https://grafana/payment",
            "log_url": "https://loki/payment",
        },
    }


@pytest.mark.asyncio
async def test_approval_notifier_parallel_success(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    notifier.configure(
        hitl_module.NotificationConfig(platform="wecom", webhook_url="https://wecom")
    )
    notifier.configure(hitl_module.NotificationConfig(platform="email", address="ops@example.com"))
    notifier.configure(hitl_module.NotificationConfig(platform="slack", channel="#sre"))

    result = await notifier.send_approval_request("alice", _sample_request_data())  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert "wecom" in result["channels"]
    assert "email" in result["channels"]
    assert len(result["errors"]) == 0
    assert len(notifier._notification_history) == 1


@pytest.mark.asyncio
async def test_approval_notifier_sequential_fallback(hitl_module, monkeypatch):
    notifier = hitl_module.ApprovalNotifier()
    notifier.configure(hitl_module.NotificationConfig(platform="wecom"))
    notifier.configure(hitl_module.NotificationConfig(platform="dingtalk"))

    monkeypatch.setattr(
        hitl_module, "_send_wecom", AsyncMock(return_value={"success": False, "error": "blocked"})
    )
    monkeypatch.setattr(hitl_module, "_send_dingtalk", AsyncMock(return_value={"success": True}))

    result = await notifier.send_approval_request(  # noqa: F841  # Variable for test verification
        "bob", _sample_request_data(), strategy="sequential"
    )
    assert result["success"] is True
    assert result["channels"] == ["dingtalk"]
    assert any("wecom: blocked" in e for e in result["errors"])
    assert len(notifier._notification_history) == 1


@pytest.mark.asyncio
async def test_approval_notifier_no_channels_configured(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    result = await notifier.send_approval_request("carol", _sample_request_data())  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert result["errors"] == ["no channels configured"]


@pytest.mark.asyncio
async def test_approval_notifier_no_valid_channel_configs(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    result = await notifier.send_approval_request(  # noqa: F841  # Variable for test verification
        "dave", _sample_request_data(), platforms=["wecom", "email"]
    )
    assert result["success"] is False
    assert result["errors"] == ["no valid channel configs"]


@pytest.mark.asyncio
async def test_approval_notifier_partial_failure_and_exception(hitl_module, monkeypatch):
    notifier = hitl_module.ApprovalNotifier()
    notifier.configure(hitl_module.NotificationConfig(platform="wecom"))
    notifier.configure(hitl_module.NotificationConfig(platform="slack", channel="#ops"))
    notifier.configure(hitl_module.NotificationConfig(platform="email", address="ops@example.com"))

    monkeypatch.setattr(hitl_module, "_send_wecom", AsyncMock(side_effect=RuntimeError("net down")))
    monkeypatch.setattr(
        hitl_module,
        "send_slack_notification",
        AsyncMock(return_value={"success": False, "error": "rate limited"}),
    )

    result = await notifier.send_approval_request("eve", _sample_request_data())  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert result["channels"] == ["email"]
    assert any("wecom" in e for e in result["errors"])
    assert any("slack" in e for e in result["errors"])


@pytest.mark.asyncio
async def test_approval_notifier_send_one_unsupported_channel(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    result = await notifier._send_one(  # noqa: F841  # Variable for test verification
        "sms",
        hitl_module.NotificationConfig(platform="sms"),
        "ops",
        _sample_request_data(),
        "msg",
    )
    assert result["success"] is False
    assert "unsupported" in result["error"]


@pytest.mark.asyncio
async def test_approval_notifier_send_one_unavailable_sender(hitl_module, monkeypatch):
    notifier = hitl_module.ApprovalNotifier()
    monkeypatch.setattr(hitl_module, "_send_wecom", None)
    result = await notifier._send_one(  # noqa: F841  # Variable for test verification
        "wecom",
        hitl_module.NotificationConfig(platform="wecom"),
        "ops",
        _sample_request_data(),
        "msg",
    )
    assert result["success"] is False
    assert "unavailable channel" in result["error"]


def test_approval_notifier_build_approval_message(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    msg = notifier._build_approval_message("alice", _sample_request_data())
    assert "Hi alice" in msg
    assert "payment service" in msg
    assert "REQ-2024-001" in msg
    assert "payment-p99" in msg
    assert "memory leak" in msg
    assert "confidence" in msg.lower()
    assert "grafana" in msg


def test_approval_notifier_build_completion_message(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    data = {
        "request_id": "REQ-002",
        "title": "Scale out",
        "context": {"result_summary": "replicas increased to 6"},
    }
    approved = notifier._build_completion_message("requester", data, True)
    assert "Approved" in approved
    assert "replicas increased" in approved

    rejected = notifier._build_completion_message("requester", data, False)
    assert "Rejected" in rejected


@pytest.mark.asyncio
async def test_approval_notifier_send_approval_complete(hitl_module):
    notifier = hitl_module.ApprovalNotifier()
    notifier.configure(hitl_module.NotificationConfig(platform="wecom"))
    result = await notifier.send_approval_complete("frank", _sample_request_data(), approved=True)  # noqa: F841  # Variable for test verification
    assert result["success"] is True
    assert "wecom" in result["channels"]


def test_approval_notifier_auto_configure_from_env(hitl_module, monkeypatch):
    import core.notify_engine as ne

    monkeypatch.setattr(
        ne,
        "NOTIFY_CONFIG",
        {
            "wecom_webhook": "https://qyapi.weixin.qq.com/fake",
            "dingtalk_webhook": "https://oapi.dingtalk.com/fake",
            "feishu_webhook": "https://open.feishu.cn/fake",
            "email_to": "ops@example.com",
        },
    )
    notifier = hitl_module.ApprovalNotifier()
    notifier.auto_configure_from_env()
    assert "wecom" in notifier.configs
    assert "dingtalk" in notifier.configs
    assert "feishu" in notifier.configs
    assert "email" in notifier.configs


def test_approval_notifier_auto_configure_unavailable(hitl_module, monkeypatch):
    monkeypatch.setattr(hitl_module, "NOTIFY_ENGINE_AVAILABLE", False)
    notifier = hitl_module.ApprovalNotifier()
    notifier.auto_configure_from_env()
    assert not notifier.configs


# ---------------------------------------------------------------------------
# core.storage.l4.storage_manager
# ---------------------------------------------------------------------------
class _FakeBackend:
    def __init__(self, config=None):
        self.config = config or {}
        self._initialized = False
        self._closed = False

    def initialize(self):
        if self.config.get("fail_init"):
            return False
        if self.config.get("raise_init"):
            raise RuntimeError("init boom")
        self._initialized = True
        return True

    def get_status(self):
        return {"initialized": self._initialized, "closed": self._closed}

    def close(self):
        if self.config.get("raise_close"):
            raise RuntimeError("close boom")
        self._closed = True


@pytest.fixture
def l4_module(monkeypatch):
    import core.storage.l4.storage_manager as mod

    monkeypatch.setattr(mod, "VictoriaMetricsStorage", _FakeBackend)
    monkeypatch.setattr(mod, "LokiStorage", _FakeBackend)
    monkeypatch.setattr(mod, "TempoStorage", _FakeBackend)
    return mod


def test_l4_manager_init_empty(l4_module):
    mgr = l4_module.L4StorageManager()
    assert mgr.initialize() is True
    assert mgr._is_initialized is True
    assert mgr.get_victoriametrics() is None
    assert mgr.get_loki() is None
    assert mgr.get_tempo() is None
    status = mgr.get_status()
    assert status["initialized"] is True
    assert status["victoriametrics"] is None


def test_l4_manager_init_all_enabled(l4_module):
    config = {
        "victoriametrics": {"enabled": True},
        "loki": {"enabled": True},
        "tempo": {"enabled": True},
    }
    mgr = l4_module.L4StorageManager(config)
    assert mgr.initialize() is True
    assert mgr.victoriametrics._initialized is True
    assert mgr.loki._initialized is True
    assert mgr.tempo._initialized is True

    status = mgr.get_status()
    assert status["victoriametrics"]["initialized"] is True
    assert status["loki"]["initialized"] is True
    assert status["tempo"]["initialized"] is True

    mgr.close()
    assert mgr._is_initialized is False


def test_l4_manager_backend_init_failure(l4_module):
    config = {"victoriametrics": {"enabled": True, "fail_init": True}}
    mgr = l4_module.L4StorageManager(config)
    assert mgr.initialize() is True
    assert mgr.victoriametrics._initialized is False


def test_l4_manager_init_exception(l4_module):
    config = {"victoriametrics": {"enabled": True, "raise_init": True}}
    mgr = l4_module.L4StorageManager(config)
    assert mgr.initialize() is False
    assert mgr._is_initialized is False


def test_l4_manager_memory_store(l4_module):
    mgr = l4_module.L4StorageManager()
    mgr.initialize()
    assert mgr.load("missing") is None
    assert mgr.load("missing", "default") == "default"
    assert mgr.save("key", {"data": [1, 2, 3]}) is True
    assert mgr.load("key") == {"data": [1, 2, 3]}


def test_l4_manager_save_error(l4_module):
    class _FaultyStore:
        def get(self, key, default=None):
            return default

        def __setitem__(self, key, value):
            raise RuntimeError("disk full")

    mgr = l4_module.L4StorageManager()
    mgr.initialize()
    mgr._memory_store = _FaultyStore()
    assert mgr.save("x", 1) is False


def test_l4_manager_close_exception(l4_module):
    config = {
        "victoriametrics": {"enabled": True},
        "loki": {"enabled": True, "raise_close": True},
    }
    mgr = l4_module.L4StorageManager(config)
    mgr.initialize()
    mgr.close()
    # exception in close() is logged, but the method returns and leaves _is_initialized unchanged
    assert mgr._is_initialized is True


def test_l4_manager_global_singleton(l4_module, monkeypatch):
    monkeypatch.setattr(l4_module, "_l4_storage_manager", None)
    mgr = l4_module.init_l4_storage_manager({"victoriametrics": {"enabled": True}})
    assert mgr is l4_module.get_l4_storage_manager()
    assert isinstance(mgr, l4_module.L4StorageManager)
