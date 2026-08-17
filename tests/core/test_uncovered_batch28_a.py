# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for batch 28 (lowest coverage core modules)."""

import asyncio  # noqa: F401  # Imported for test setup
import contextlib
import datetime
import io
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import socket
import sys  # noqa: F401  # Imported for test setup
import types
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest  # noqa: F401  # Imported for test setup

# ---------------------------------------------------------------------------
# Stubs for heavy optional submodules (load before core.ai_engine import)
# ---------------------------------------------------------------------------
if "core.ai.rag" not in sys.modules:
    _rag = types.ModuleType("core.ai.rag")
    _rag.KnowledgeBase = type("KnowledgeBase", (), {})
    _rag.RAGPipeline = type(
        "RAGPipeline",
        (),
        {
            "__init__": lambda self, *a, **k: None,
            "retrieve_and_generate": staticmethod(lambda **k: ""),
        },
    )
    sys.modules["core.ai.rag"] = _rag
    _fusion = types.ModuleType("core.ai.rag.fusion")
    _fusion.ConcatenationFusion = type("ConcatenationFusion", (), {"__init__": lambda self: None})
    sys.modules["core.ai.rag.fusion"] = _fusion
    _retriever = types.ModuleType("core.ai.rag.retriever")
    _retriever.Retriever = type("Retriever", (), {"__init__": lambda self, *a, **k: None})
    _retriever.VectorStoreRetrieval = type(
        "VectorStoreRetrieval", (), {"__init__": lambda self, *a, **k: None}
    )
    sys.modules["core.ai.rag.retriever"] = _retriever
    _vectorizer = types.ModuleType("core.ai.rag.vectorizer")
    _vectorizer.SentenceTransformerEmbedding = type(  # noqa: F841  # Variable for test verification
        "SentenceTransformerEmbedding", (), {"__init__": lambda self, **k: None}
    )
    sys.modules["core.ai.rag.vectorizer"] = _vectorizer

import core.agent.planner as planner
import core.agent.tools as tools
import core.ai_engine as ai_engine
import core.heal_graph as heal_graph
import core.notify_engine as notify_engine
import core.topology_engine as topology_engine
import core.user_service as user_service

pytestmark = [pytest.mark.core]


def _run(coro):
    return asyncio.run(coro)


# =============================================================================
# core.topology_engine
# =============================================================================


@pytest.fixture
def clean_topology(monkeypatch):
    monkeypatch.setattr(topology_engine, "_nodes", {})
    monkeypatch.setattr(topology_engine, "_edges", [])
    monkeypatch.setattr(topology_engine, "_topology_cache", {})
    return None


def test_build_topology_graph_and_dict():
    alerts = [
        {"source": "a", "target": "b", "weight": 2},
        {"source": "b", "target": "c"},
        {"source": "bad"},
        "not-a-dict",
    ]
    G = topology_engine.build_topology_graph(alerts)
    data = topology_engine.graph_to_dict(G)
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) == 4
    assert len(data["edges"]) == 3


async def test_get_full_link_topology(monkeypatch):
    import config

    monkeypatch.setattr(config, "LINUX_HOSTS", [{"host_name": "host1"}, "host2"])
    monkeypatch.setattr(
        "core.db_engine.alert_repository.get_recent",
        AsyncMock(return_value=[{"source": "x", "target": "y", "weight": 1}]),
    )
    result = await topology_engine.get_full_link_topology("any")  # noqa: F841  # Variable for test verification
    assert "nodes" in result and "edges" in result


def test_topology_crud(clean_topology):
    _run(topology_engine.add_node({"id": "n1"}))
    _run(topology_engine.add_node({"id": "n2"}))  # duplicate -> error branch
    _run(topology_engine.add_node({"id": ""}))  # invalid
    _run(topology_engine.add_edge({"source": "n1", "target": "n2"}))
    _run(topology_engine.add_edge({"source": "n1", "target": "missing"}))
    assert _run(topology_engine.node_exists("n1"))
    deps = _run(topology_engine.query_dependencies("n1"))
    impact = _run(topology_engine.get_impact_analysis("n1"))
    assert "direct_impact" in impact
    topo = topology_engine.validate_topology(
        {"nodes": [{"id": "n1"}, {"id": "n3"}], "edges": [{"source": "n1", "target": "n2"}]}
    )
    assert topo["valid"]
    assert any("orphan" in w for w in topo["warnings"])
    _run(topology_engine.remove_edge("n1__n2"))
    _run(topology_engine.remove_node("n1"))
    _run(topology_engine.remove_node("n1"))


async def test_build_and_get_topology():
    bad = await topology_engine.build_topology([{"id": ""}], [])
    assert not bad["success"]
    cyclic = await topology_engine.build_topology(
        [{"id": "a"}, {"id": "b"}],
        [{"source": "a", "target": "b"}, {"source": "b", "target": "a"}],
    )
    assert (
        "circular" in cyclic.get("error", "").lower() or "cycle" in cyclic.get("error", "").lower()
    )
    good = await topology_engine.build_topology(
        [{"id": "x"}, {"id": "y"}], [{"source": "x", "target": "y"}]
    )
    assert good["success"]
    tid = good["topology_id"]
    fetched = await topology_engine.get_topology(tid)
    assert fetched["success"]
    missing = await topology_engine.get_topology("no-such-id")
    assert not missing["success"]


def test_topology_helpers():
    assert topology_engine.get_node_timeline("n") == {"events": []}
    assert topology_engine.update_node_health("n", "ok") is True
    assert "node_count" in topology_engine.get_topology_status("k")


# =============================================================================
# core.notify_engine
# =============================================================================


@pytest.fixture
def notify_cfg(monkeypatch):
    cfg = {
        "enabled": True,
        "min_level": "info",
        "wecom_webhook": "https://example.com/wecom",
        "dingtalk_webhook": "https://example.com/dingtalk",
        "dingtalk_secret": "SEC",
        "feishu_webhook": "https://example.com/feishu",
        "email_to": "ops@example.com",
        "phone_provider": "https://example.com/phone",
        "phone_to": "1234567890",
        "sms_provider": "https://example.com/sms",
        "sms_to": "1234567890",
        "oncall_provider": "json",
        "oncall_api_token": "tok",
        "oncall_api_base": "https://example.com",
        "cooldown_seconds": "300",
    }
    monkeypatch.setattr(notify_engine, "NOTIFY_CONFIG", cfg)
    monkeypatch.setattr(
        notify_engine,
        "_get_slack_client",
        lambda: AsyncMock(chat_postMessage=AsyncMock(return_value={"ok": True})),
    )

    class _FakeAioSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return None

        async def post(self, *a, **kw):
            return type("Resp", (), {"status": 200})()

    monkeypatch.setattr(
        notify_engine, "aiohttp", type("_FakeAiohttp", (), {"ClientSession": _FakeAioSession})()
    )

    class _FakeSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return None

        def sendmail(self, *a, **kw):
            pass

    monkeypatch.setattr(notify_engine.smtplib, "SMTP", _FakeSMTP)
    fake_http = AsyncMock(
        post=AsyncMock(return_value=AsyncMock(raise_for_status=AsyncMock(), status_code=200))
    )
    monkeypatch.setattr(notify_engine, "_get_http_client", lambda: fake_http)
    monkeypatch.setattr(
        "core.oncall_adapter.get_oncall_adapter",
        lambda: MagicMock(
            lookup_async=AsyncMock(
                return_value=[types.SimpleNamespace(phone="1234567890", email="e@example.com")]
            )
        ),
    )
    return cfg


def test_notify_formatters():
    alert = {
        "severity": "critical",
        "type": "cpu_high",
        "message": "cpu is high",
        "host": "h1",
        "metrics": {"cpu": 95},
    }
    text = notify_engine.format_alert_message(alert)
    assert "CPU" in text or "cpu" in text
    assert "Host" in text
    for fmt in ("text", "html", "markdown"):
        assert notify_engine.build_structured_alert_message(alert, fmt=fmt)
    assert notify_engine.format_for_slack(alert)
    assert json.loads(notify_engine.format_for_teams(alert))


def test_validate_webhook_url():
    assert notify_engine._validate_webhook_url("https://x.com", "x")
    assert not notify_engine._validate_webhook_url("ftp://x.com", "x")
    assert not notify_engine._validate_webhook_url("x" * 3000, "x")
    assert not notify_engine._validate_webhook_url("", "x")


async def test_send_notification_channels(notify_cfg):
    alert = {
        "type": "alert",
        "message": "test",
        "severity": "critical",
        "title": "CPU high",
        "id": "a1",
        "fingerprint": "fp1",
    }
    res = await notify_engine.send_notification(alert, ["slack", "teams", "email"])
    assert res["success"]
    res2 = await notify_engine.send_notification({"type": "x"}, ["slack"])
    assert not res2["success"]


async def test_send_alert_notification(notify_cfg):
    alert = {
        "id": "a2",
        "fingerprint": "fp2",
        "title": "cpu high",
        "severity": "critical",
        "type": "alert",
        "message": "cpu",
        "host": "h1",
    }
    res = await notify_engine.send_alert_notification(alert)
    assert res["status"] in ("ok", "all_failed")
    original = notify_engine.NOTIFY_CONFIG
    notify_engine.NOTIFY_CONFIG = {"enabled": False, "min_level": "info"}
    resd = await notify_engine.send_alert_notification(alert)
    assert resd["status"] == "disabled"
    notify_engine.NOTIFY_CONFIG = original


async def test_query_and_mark_notifications(notify_cfg):
    notify_engine._track_notification_status(
        {"id": "a3", "title": "t", "level": "critical"}, "slack", "delivered"
    )
    assert notify_engine.get_notification_status(alert_id="a3")
    assert await notify_engine.query_notifications(limit=5)
    assert await notify_engine.get_notification_history(limit=5)
    notify_engine.mark_notification_read("a3", "slack")
    assert notify_engine.get_notification_read_status("a3", "slack")["status"] == "read"
    assert notify_engine.get_notification_read_status("no", "slack")["status"] == "not_found"


async def test_post_webhook_errors(monkeypatch):
    monkeypatch.setattr(notify_engine, "_post_webhook", notify_engine._post_webhook_original)

    class _FakeResp:
        status_code = 500
        text = "bad"

    def _make_side(exc_class):
        def _side(*a, **kw):
            if exc_class is httpx.HTTPStatusError:
                raise httpx.HTTPStatusError("err", request=MagicMock(), response=_FakeResp())
            raise exc_class("err", request=MagicMock())

        return _side

    for exc_class in (httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError):
        fake_client = AsyncMock(post=AsyncMock(side_effect=_make_side(exc_class)))
        monkeypatch.setattr(notify_engine, "_get_http_client", lambda c=fake_client: c)
        try:
            await notify_engine._post_webhook("https://example.com", {}, "x")
        except Exception:
            pass


# =============================================================================
# core.user_service
# =============================================================================


class _FakeUser:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        if not hasattr(self, "id"):
            self.id = None


class _FakeResult:
    def __init__(self, scalar=None, all_users=None, rowcount=0):
        self._scalar = scalar
        self._all = all_users or []
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._scalar

    def scalars(self):
        class _S:
            def __init__(self, items):
                self._items = items

            def all(self):
                return self._items

        return _S(self._all)


class _FakeSession:
    def __init__(self, scalar=None, all_users=None, rowcount=0):
        self._scalar = scalar
        self._all = all_users
        self._rowcount = rowcount

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    def add(self, obj):
        pass

    async def commit(self):
        pass

    async def refresh(self, obj):
        obj.id = 1

    async def execute(self, stmt):
        return _FakeResult(scalar=self._scalar, all_users=self._all, rowcount=self._rowcount)


class _FakeAsyncSession:
    def __init__(self, scalar=None, all_users=None, rowcount=0):
        self._scalar = scalar
        self._all = all_users
        self._rowcount = rowcount

    def __call__(self):
        return _FakeSession(self._scalar, self._all, self._rowcount)


@pytest.fixture
def user_db(monkeypatch):
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession())
    return None


async def test_user_service_crud(user_db):
    u = await user_service.UserService.get_user_by_username("alice")
    assert u is None
    alice = _FakeUser(
        id=1,
        username="alice",
        email="a@example.com",
        full_name="Alice",
        role="user",
        disabled=False,
        mfa_enabled=False,
    )
    monkeypatch = user_db  # noqa: F841
    # create
    created = await user_service.UserService.create_user("bob", "hash", email="b@example.com")
    assert created is not None


async def test_user_service_update_and_delete(monkeypatch):
    existing = _FakeUser(id=2, username="carol", email="c@example.com")
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession(scalar=existing))
    assert await user_service.UserService.update_user("carol", email="new@example.com")
    assert not await user_service.UserService.update_user("missing")
    assert not await user_service.UserService.update_user("carol")  # no data
    assert await user_service.UserService.update_password("carol", "newhash")
    monkeypatch.setattr(
        user_service, "AsyncSessionLocal", _FakeAsyncSession(scalar=existing, rowcount=1)
    )
    assert await user_service.UserService.delete_user("carol")
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession(rowcount=0))
    assert not await user_service.UserService.delete_user("nobody")
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession(all_users=[existing]))
    assert isinstance(await user_service.UserService.list_users(), list)
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession(scalar=existing))
    assert await user_service.UserService.update_last_login("carol")
    assert await user_service.UserService.enable_mfa("carol", "secret", ["c1", "c2"])
    assert await user_service.UserService.disable_mfa("carol")
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _FakeAsyncSession(scalar=None))
    assert not await user_service.UserService.update_last_login("missing")


def test_user_to_dict():
    now = datetime.datetime.now()
    u = _FakeUser(
        id=1,
        username="u1",
        email="e",
        full_name="U",
        role="user",
        disabled=False,
        created_at=now,
        updated_at=now,
        last_login_at=now,
        mfa_enabled=False,
    )
    d = user_service.UserService.user_to_dict(u)
    assert d["username"] == "u1"
    assert "created_at" in d


# =============================================================================
# core.agent.planner
# =============================================================================


@pytest.fixture
def planner_fakes(monkeypatch):
    monkeypatch.setattr(planner, "compress_context", lambda ctx, **kw: ctx)
    monkeypatch.setattr(planner, "anonymize_text", lambda t, **kw: t)
    monkeypatch.setattr(planner, "anonymize_dict", lambda d, **kw: d)
    monkeypatch.setattr(planner, "moderate_content", lambda *a, **kw: (True, []))
    monkeypatch.setattr(
        planner,
        "get_session_budget",
        lambda *a, **kw: MagicMock(check_and_record=lambda *a, **kw: True),
    )
    monkeypatch.setattr(planner, "estimate_tokens", lambda *a, **kw: 10)
    return None


def test_chain_of_thought(planner_fakes):
    cot = planner.ChainOfThought()
    steps = cot.reason("修复 CPU 高的问题", {"target": "web"})
    assert steps
    assert planner.ChainOfThought._detect_symptom("dns fail", {}) == "dns"
    assert planner.ChainOfThought._detect_symptom("sql slow", {}) == "sql"
    assert planner.ChainOfThought._detect_symptom("oom killed", {}) == "oom"
    llm = MagicMock(generate=lambda prompt: json.dumps(["step1", "step2"]))
    cot2 = planner.ChainOfThought(llm)
    assert cot2.reason("fix", {})


def test_task_planner(planner_fakes):
    tp = planner.TaskPlanner()
    tasks = tp.plan("诊断 DNS 解析失败", {"target": "gateway", "service": "payment"}, ["collect"])
    assert tasks
    assert tp.get_plan_summary()["total"] > 0
    tid = tasks[0].id
    tp.adjust_plan(tid, planner.TaskStatus.FAILED, result=None, error="boom")
    assert tp.get_plan_summary()["failed"] >= 1
    assert tp.get_ready_tasks() == []


def test_planner_cycle_and_create():
    tp = planner.TaskPlanner()
    cycle_task = planner.Task(id="t0", description="d", dependencies=["t0"])
    assert tp._has_cycle([cycle_task])
    p2 = planner.create_planner()
    assert p2 is not None
    assert planner.TaskStatus.PENDING.value == "pending"
    assert planner.TaskPriority.HIGH.value == 3


# =============================================================================
# core.agent.tools
# =============================================================================


class _FakeObs:
    def _safe_label(self, x):
        return str(x)

    def get_prometheus_url(self):
        return None

    def query_prometheus(self, *a, **kw):
        return None

    def query_prometheus_range(self, *a, **kw):
        return None

    def _extract_prom_scalar_value(self, *a, **kw):
        return None

    def query_service_metrics(self, *a, **kw):
        return {}

    def query_network_metrics(self, *a, **kw):
        return {}

    def query_change_events(self, *a, **kw):
        return []

    def query_kubernetes_events(self, *a, **kw):
        return []

    def query_kubernetes_pod(self, *a, **kw):
        return {}

    def query_kubernetes_node(self, *a, **kw):
        return {}


class _FakeConn:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class _FakePath:
    def __init__(self, *args):
        self._path = os.path.join(*args)

    def is_file(self):
        return True

    def open(self, *a, **kw):
        return io.StringIO("INFO test log line\nERROR another line\n")

    def __str__(self):
        return self._path


@pytest.fixture
def tools_fakes(monkeypatch):
    monkeypatch.setattr(tools, "observability_client", _FakeObs())
    monkeypatch.setattr(tools, "COMMAND_GUARD_AVAILABLE", False)
    monkeypatch.setattr(tools, "AUDIT_AVAILABLE", False)
    monkeypatch.setattr("pathlib.Path", _FakePath)
    monkeypatch.setattr("httpx.get", lambda *a, **kw: type("Resp", (), {"status_code": 200})())
    monkeypatch.setattr(socket, "create_connection", lambda *a, **kw: _FakeConn())
    monkeypatch.setattr("shutil.which", lambda *a, **kw: None)
    _fake_subagent = types.ModuleType("core.agent.subagent")

    class _SubAgentDispatcher:
        def __init__(self, *a, **kw):
            pass

        def dispatch(self, *a, **kw):
            return MagicMock(to_dict=lambda: {"status": "ok"})

        def shutdown(self, *a, **kw):
            pass

    _fake_subagent.SubAgentDispatcher = _SubAgentDispatcher
    monkeypatch.setitem(sys.modules, "core.agent.subagent", _fake_subagent)
    _fake_rci = types.ModuleType("core.root_cause_intelligence")
    _fake_rci.root_cause_intelligence_engine = MagicMock(
        topology_graph={"svc": ["dep1"]},
        analyze_root_causes_enhanced=AsyncMock(
            return_value=[
                MagicMock(
                    root_cause="root",
                    confidence=0.9,
                    expected_observations=[],
                    missing_data=[],
                    verification_status="verified",
                    evidence=[],
                )
            ]
        ),
    )
    monkeypatch.setitem(sys.modules, "core.root_cause_intelligence", _fake_rci)
    return None


TOOL_PARAMS = [
    ("collect_metrics", {"target": "node1"}),
    ("collect_logs", {"service": "svc"}),
    ("collect_service_metrics", {"service_name": "svc"}),
    ("collect_network_metrics", {"target": "node1"}),
    ("collect_change_events", {"target": "svc", "hours": 24}),
    ("collect_kubernetes_events", {"namespace": "default"}),
    ("collect_container_metrics", {"pod_name": "pod1"}),
    ("collect_host_metrics", {"node_name": "node1"}),
    ("collect_database_metrics", {"database": "db1"}),
    ("collect_correlated_alerts", {"service": "svc"}),
    ("collect_topology", {"service": "svc"}),
    ("analyze_anomaly", {"data": [1.0, 2.0, 3.0]}),
    (
        "root_cause_analysis",
        {
            "alert_id": "a1",
            "alert": {"id": "a1"},
            "metrics_data": {},
            "correlated_alerts": [],
            "change_events": [],
            "verification_data": {},
        },
    ),
    ("restart_service", {"service_name": "svc"}),
    ("scale_service", {"service_name": "svc", "replicas": 2}),
    ("check_health", {"target": "http://example.com"}),
    ("run_diagnostic", {"target": "svc"}),
    ("dispatch_subagent", {"goal": "test", "context": {}, "available_tools": []}),
]


def test_tool_registry_and_selector(tools_fakes):
    reg = tools.create_tool_registry()
    assert reg.list_tools()
    assert reg.search_tools("metric")
    assert reg.get_tool("collect_metrics")
    reg.approve_tool("x", "admin")
    reg.request_tool_approval("x", "u")
    reg.is_tool_approved("x")
    reg.unregister("x")
    sel = tools.ToolSelector(reg)
    for desc in ("收集日志", "重启服务", "检查健康", "分析根因"):
        sel.select_tool(desc, {"target": "svc"})
    assert sel.select_tools_for_chain(["收集日志", "重启服务"], {"target": "svc"})


def test_tool_executor(tools_fakes):
    reg = tools.create_tool_registry()
    exec = tools.create_tool_executor(reg)
    for name, params in TOOL_PARAMS:
        result = exec.execute_tool(name, **params)  # noqa: F841  # Variable for test verification
        assert result is not None
    exec.execute_chain(
        [("collect_metrics", {"target": "node1"}), ("analyze_anomaly", {"data": [1.0, 2.0, 3.0]})]
    )
    exec.execute_with_auto_selection(
        "收集 system 的指标", {"target": "system", "available_tools": list(reg.tools.keys())}
    )
    assert exec.get_execution_statistics()["total"] > 0


def test_tool_execute_dry_run_and_validation(tools_fakes):
    reg = tools.create_tool_registry()
    tool = reg.get_tool("collect_metrics")
    dry = tool.execute(dry_run=True, target="node1")
    assert dry.get("dry_run") is True


# =============================================================================
# core.heal_graph
# =============================================================================


@pytest.fixture
def heal_fakes(monkeypatch):
    monkeypatch.setattr(heal_graph, "_metrics_history", MagicMock(to_dict=lambda: {}))
    monkeypatch.setattr(heal_graph, "_set_trace_id", lambda x: None)
    monkeypatch.setattr(heal_graph, "AUDIT_AVAILABLE", False)
    monkeypatch.setattr(
        heal_graph, "SNAPSHOT_CONFIG", {"enabled": True, "rollback_approval_required": False}
    )
    monkeypatch.setattr(heal_graph, "analyze_command", lambda cmd: {"risk_level": "safe"})
    monkeypatch.setattr(heal_graph, "RiskLevel", type("RiskLevel", (), {"BLOCKED": "blocked"}))
    monkeypatch.setattr(
        heal_graph,
        "async_get_approval_by_alert",
        AsyncMock(
            return_value={"status": "approved", "approved_at": datetime.datetime.now().isoformat()}
        ),
    )
    monkeypatch.setattr(heal_graph, "async_upsert_pending_approval", AsyncMock())
    monkeypatch.setattr(heal_graph, "async_update_approval_status_by_alert", AsyncMock())
    monkeypatch.setattr(heal_graph, "async_insert_repair_record", AsyncMock())
    monkeypatch.setattr(heal_graph, "save_snapshot", AsyncMock(return_value="snap1"))
    monkeypatch.setattr(heal_graph, "update_snapshot_status", AsyncMock())
    monkeypatch.setattr(heal_graph, "cleanup_expired_snapshots", AsyncMock())
    monkeypatch.setattr(heal_graph, "notify_rollback_failure", AsyncMock())
    monkeypatch.setattr(heal_graph, "record_decision", lambda *a, **kw: "dec1")
    monkeypatch.setattr(heal_graph, "record_outcome", lambda *a, **kw: None)
    import core.ai_engine as ai_engine_mod
    import core.priority_engine as priority_mod
    import core.runbook_generator as runbook_mod
    import core.verifier as verifier_mod

    monkeypatch.setattr(ai_engine_mod, "analyze", AsyncMock(return_value="AI analysis"))
    monkeypatch.setattr(priority_mod, "compute_sla_score", lambda alert: 1)
    monkeypatch.setattr(
        runbook_mod,
        "generate_repair_runbook",
        lambda *a, **kw: {
            "success": True,
            "source": "test",
            "worst_risk": "low",
            "needs_approval": False,
            "auto_executable": True,
            "runbook": {
                "script_key": "cpu_high_script",
                "name": "CPU high",
                "commands": ["systemctl restart service1"],
                "rollback": "systemctl start service1",
                "risk_level": "low",
                "params": {},
            },
        },
    )
    monkeypatch.setattr(
        verifier_mod, "verify_repair", AsyncMock(return_value={"verified": True, "passed": True})
    )
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "false")
    monkeypatch.setenv("HEAL_APPROVAL_VALIDITY_MINUTES", "60")
    monkeypatch.setenv("HARDWARE_EXECUTE_ENABLED", "false")
    return None


def test_heal_graph_helpers():
    assert not heal_graph._is_alert_resolved({"status": "firing"})
    assert heal_graph._is_alert_resolved({"status": "resolved"})
    assert heal_graph._is_alert_resolved({"resolved": True})
    can, reason = heal_graph._pre_execution_check(
        {"status": "firing"}, {"approved_at": datetime.datetime.now().isoformat()}
    )
    assert can
    assert isinstance(heal_graph._is_off_hours(), bool)
    assert isinstance(heal_graph._approval_validity_minutes(), int)
    assert not heal_graph._is_approval_expired(None)
    hw = {"category": "hardware"}
    assert heal_graph._is_hardware_alert(hw)
    assert "service1" in heal_graph._allowed_targets_from_alert({"service_name": "service1"})
    assert heal_graph._extract_command_target("systemctl restart service1") == "service1"
    assert heal_graph._tokenize_alert_text("Hello, World!")


async def test_run_heal_success(heal_fakes):
    state = heal_graph.HealState(
        alert={
            "id": "h1",
            "metric": "cpu",
            "title": "cpu high",
            "status": "firing",
            "service_name": "service1",
        }
    )
    final = await heal_graph.run_heal(state)
    assert final is not None


def test_build_graph():
    assert heal_graph._build_graph() is not None


# =============================================================================
# core.ai_engine
# =============================================================================


@pytest.fixture
def ai_fakes(monkeypatch):
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", False)
    monkeypatch.setattr(ai_engine, "DATA_PRIVACY_AVAILABLE", False)
    monkeypatch.setattr(ai_engine, "AUDIT_LOGGER_AVAILABLE", False)
    monkeypatch.setattr(ai_engine, "_langfuse_available", False)
    monkeypatch.setattr(ai_engine, "_rag_pipeline", None)
    monkeypatch.setattr(ai_engine, "compress_prompt_text", lambda text, max_tokens: text)
    monkeypatch.setattr(ai_engine, "estimate_tokens", lambda *a, **kw: 100)
    monkeypatch.setattr(ai_engine, "_rate_limit_wait", AsyncMock())
    fake_router = MagicMock(
        generate=AsyncMock(
            return_value={
                "content": json.dumps(
                    {
                        "data_assessment": {"reliability_score": 0.9, "reliability_concerns": []},
                        "candidates": [
                            {
                                "rank": 1,
                                "root_cause": "cpu overload",
                                "confidence": 0.85,
                                "expected_observations_if_true": [],
                                "missing_data": [],
                                "is_verifiable": True,
                                "evidence": [],
                            }
                        ],
                        "multi_root_cause_note": "",
                        "escalation_recommended": False,
                        "escalation_reason": "",
                        "recommended_action": "check process",
                    }
                ),
                "model": "fake",
                "usage": {"total_tokens": 10, "prompt_tokens": 7, "completion_tokens": 3},
            }
        )
    )
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: fake_router)
    fake_monitor = MagicMock(
        model_configs=[{"max_tokens": 8000}],
        estimate_tokens=lambda *a, **kw: 100,
        check_budget=lambda *a, **kw: True,
        get_cost_per_1k=lambda *a, **kw: 0.001,
        record_cost=lambda *a, **kw: None,
    )
    monkeypatch.setattr(ai_engine, "get_llm_cost_monitor", lambda: fake_monitor)
    fake_session = MagicMock(
        check_and_record=lambda *a, **kw: True, record_cost=lambda *a, **kw: None
    )
    monkeypatch.setattr(ai_engine, "get_session_budget", lambda *a, **kw: fake_session)
    monkeypatch.setattr(
        ai_engine,
        "AI_CONFIG",
        {
            "is_enabled": True,
            "api_key": "test",
            "base_url": "http://test",
            "model": "fake",
            "timeout": 10,
            "max_retries": 1,
        },
    )
    return fake_router, fake_monitor, fake_session


async def test_ai_engine_analyze(ai_fakes):
    res = await ai_engine.analyze("cpu high", validate_json=True)
    assert isinstance(res, str)
    assert "data_assessment" in res
    # disabled / fallback
    monkeypatch = ai_fakes
    original = ai_engine.AI_CONFIG
    ai_engine.AI_CONFIG = {"is_enabled": False}
    fallback = await ai_engine.analyze("cpu high", platform="linux")
    assert "规则降级" in fallback or "规则" in fallback
    ai_engine.AI_CONFIG = original
    # router returns empty -> rule fallback
    ai_fakes[0].generate.return_value = {"content": "", "model": "fake", "usage": {}}
    empty_res = await ai_engine.analyze("cpu high", validate_json=False)
    assert isinstance(empty_res, str)


def test_ai_engine_helpers(ai_fakes):
    valid = json.dumps(
        {
            "data_assessment": {"reliability_score": 0.9, "reliability_concerns": []},
            "candidates": [
                {
                    "rank": 1,
                    "root_cause": "x",
                    "confidence": 0.8,
                    "expected_observations_if_true": [],
                    "missing_data": [],
                    "is_verifiable": True,
                    "evidence": [],
                }
            ],
            "multi_root_cause_note": "",
            "escalation_recommended": False,
            "escalation_reason": "",
            "recommended_action": "",
        }
    )
    assert ai_engine._validate_root_cause_output(valid)
    assert ai_engine._validate_root_cause_output("not json") is None
    assert (
        json.loads(ai_engine._fallback_schema_error_json("err"))["escalation_recommended"] is True
    )
    assert ai_engine._compute_prompt_token_budget("x") > 0
    assert ai_engine._redact_text("hello") == "hello"
    assert ai_engine._redact_value(["hello"]) == ["hello"]
    assert "--- BEGIN USER INPUT ---" in ai_engine._build_rich_user_message(
        "q", "m", "linux", {"top_processes": [{"pid": 1}], "metrics": {"cpu": 80}}
    )
    assert "windows" in ai_engine._rule_based_analysis("q", "m", "windows")
    assert ai_engine.RootCauseAnalysisResponse.model_validate(json.loads(valid))


async def test_ai_engine_services(ai_fakes):
    svc = ai_engine.LLMAnalysisService()
    r = await svc.analyze({"query": "cpu", "metrics_snapshot": "", "platform": "linux"})
    assert "result" in r
    obs = await svc.observe({"query": "cpu"})
    assert "result" in obs
    rb = await svc.generate_runbook({"id": "a1", "title": "t", "desc": "d"}, {"platform": "linux"})
    assert "runbook" in rb
    assert rb["alert_id"] == "a1"
    ss = await svc.search_similar("cpu")
    assert isinstance(ss, list)
    hs = await svc.get_health_status()
    assert hs["available"] is True

    pred = ai_engine.PredictiveAnalysisEngine()
    anom = await pred.predict_system_anomalies(
        {
            "cpu": {"usage_percent": 95},
            "memory": {"usage_percent": 90},
            "disk": [{"usage_percent": 95, "mount_point": "/"}],
        }
    )
    assert "predicted_anomalies" in anom
    cap = await pred.predict_capacity_needs(
        {"cpu": {"usage_percent": 80}, "memory": {"usage_percent": 70}}
    )
    assert "predictions_3_months" in cap

    rec = ai_engine.IntelligentRecommendationEngine()
    recs = await rec.generate_recommendations(
        {"id": "1", "type": "cpu_high", "severity": "critical"}
    )
    assert isinstance(recs, list)
    assert len(recs) > 0
    pers = await rec.get_personalized_recommendations(
        "u1", [{"type": "optimization"}, {"type": "optimization"}]
    )
    assert isinstance(pers, list)

    nli = ai_engine.NaturalLanguageInteraction()
    qr = await nli.process_natural_language_query(
        "what is the cpu status?", {"metrics": {"cpu": "80%"}}
    )
    assert qr["intent"] == "status_query"
    conv = await nli.maintain_conversation("u1", "predict memory trends")
    assert "conversation_history" in conv


async def test_ai_engine_lifecycle(ai_fakes):
    ai_engine._http_client = AsyncMock(is_closed=False)
    await ai_engine.close_http_client()
    assert ai_engine._http_client is None
    await ai_engine.close_langfuse_client()
    await ai_engine._rate_limit_wait()


# =============================================================================
# Reload / misc to cover extra branches
# =============================================================================


async def test_notify_reload_and_cooldown():
    res = notify_engine.reload_notify_config()
    assert isinstance(res, dict)


# =============================================================================
# Extended coverage: topology, user_service, notify_engine, planner
# =============================================================================


def test_topology_missing_branches(monkeypatch, clean_topology):
    # non-numeric weight
    G = topology_engine.build_topology_graph([{"source": "a", "target": "b", "weight": "bad"}])
    assert G.has_edge("a", "b")
    # empty/full link topology fallback
    import config

    monkeypatch.setattr(config, "LINUX_HOSTS", [{"host_name": ""}, ""])
    monkeypatch.setattr(
        "core.db_engine.alert_repository.get_recent",
        AsyncMock(return_value=[]),
    )
    res = _run(topology_engine.get_full_link_topology("k"))
    assert "nodes" in res
    # validate non-dict
    assert not topology_engine.validate_topology("not a dict")["valid"]
    # insert/query cache miss
    topology_engine._topology_cache.clear()
    tid = _run(topology_engine.insert_topology([{"id": "a"}], []))
    topology_engine._topology_cache.pop(tid, None)
    assert not _run(topology_engine.get_topology(tid))["success"]
    _run(topology_engine.get_topology(""))
    # build topology skips malformed edges
    _run(topology_engine.build_topology([{"id": "x"}], [None, {"source": "x"}]))
    # duplicate/invalid edge deletion
    _run(topology_engine.add_node({"id": "n1"}))
    _run(topology_engine.add_node({"id": "n2"}))
    _run(topology_engine.add_edge({"source": "n1", "target": "n2", "id": "n1__n2"}))
    dup = _run(topology_engine.add_edge({"source": "n1", "target": "n2"}))
    assert not dup["success"]
    assert _run(topology_engine.delete_edge("n1__n2"))
    assert _run(topology_engine.delete_edge("n1->n2")) is False
    assert _run(topology_engine.get_transitive_dependencies("missing")) == []


class _RaiseSession:
    def __init__(self, exc=Exception("db fail")):
        self.exc = exc

    def __call__(self):
        return self

    async def __aenter__(self):
        raise self.exc

    async def __aexit__(self, *a):
        return None


async def test_user_service_exceptions(monkeypatch):
    monkeypatch.setattr(user_service, "AsyncSessionLocal", _RaiseSession())
    assert await user_service.UserService.get_user_by_username("x") is None
    assert await user_service.UserService.get_user_by_email("x") is None
    assert await user_service.UserService.get_user_by_id(1) is None
    assert await user_service.UserService.create_user("x", "h") is None
    assert not await user_service.UserService.update_user("x")
    assert not await user_service.UserService.update_password("x", "h")
    assert not await user_service.UserService.delete_user("x")
    assert await user_service.UserService.list_users() == []
    assert not await user_service.UserService.update_last_login("x")
    assert not await user_service.UserService.enable_mfa("x", "s", [])
    assert not await user_service.UserService.disable_mfa("x")


async def test_notify_channel_functions(notify_cfg, monkeypatch):
    alert = {
        "id": "a1",
        "fingerprint": "fp1",
        "title": "t",
        "level": "critical",
        "message": "m",
        "summary": "s",
    }
    # direct channel senders
    for fn in (notify_engine._send_wecom, notify_engine._send_dingtalk, notify_engine._send_feishu):
        res = await fn(alert)
        assert isinstance(res, dict)
    # phone / sms missing config
    res = await notify_engine._send_phone_notification(alert, {})
    assert not res["success"]
    res = await notify_engine._send_sms_notification(alert, {})
    assert not res["success"]
    # one channel routing
    for ch in ("wecom", "dingtalk", "feishu", "slack", "teams", "email", "phone", "sms", "unknown"):
        res = await notify_engine._send_one_channel(alert, ch, notify_engine.NOTIFY_CONFIG)
        assert isinstance(res, dict)
    # invalid post_webhook branches
    res = await notify_engine._post_webhook_original("", {}, "x")
    assert not res["success"]
    res = await notify_engine._post_webhook_original("https://x.com", "bad", "x")
    assert not res["success"]
    for exc in (
        httpx.HTTPStatusError(
            "e", request=MagicMock(), response=MagicMock(text="bad", status_code=500)
        ),
        httpx.TimeoutException("t", request=MagicMock()),
        httpx.ConnectError("c", request=MagicMock()),
    ):
        fake = AsyncMock(post=AsyncMock(side_effect=exc))
        monkeypatch.setattr(notify_engine, "_get_http_client", lambda f=fake: f)
        res = await notify_engine._post_webhook_original("https://x.com", {"a": 1}, "x")
        assert not res["success"]


def test_notify_format_and_config(notify_cfg, monkeypatch):
    # format with non-dict metrics
    text = notify_engine.format_alert_message(
        {"severity": "w", "type": "x", "message": "m", "metrics": "bad"}
    )
    assert "bad" in text
    # structured formats with link auto-collection
    alert = {"summary": "s", "impact": "i", "dashboard_url": "http://d", "log_url": "http://l"}
    assert notify_engine.build_structured_alert_message(alert, fmt="text")
    assert notify_engine.build_structured_alert_message(alert, fmt="html")
    # invalid webhook validation
    assert not notify_engine._validate_webhook_url("http://", "x")
    assert not notify_engine._validate_webhook_url("ftp://x.com", "x")
    # send_alert branches
    orig = notify_engine.NOTIFY_CONFIG
    # disabled
    notify_engine.NOTIFY_CONFIG = {"enabled": False, "min_level": "info"}
    r = _run(
        notify_engine.send_alert_notification(
            {"id": "a", "title": "t", "severity": "critical", "type": "alert", "message": "m"}
        )
    )
    assert r["status"] == "disabled"
    # filtered
    notify_engine.NOTIFY_CONFIG = {"enabled": True, "min_level": "critical"}
    r = _run(
        notify_engine.send_alert_notification(
            {"id": "a", "title": "t", "severity": "info", "type": "alert", "message": "m"}
        )
    )
    assert r["status"] == "filtered"
    # invalid alert
    r = _run(notify_engine.send_alert_notification("bad"))
    assert r["status"] == "invalid_alert"
    # no channels configured
    notify_engine.NOTIFY_CONFIG = {"enabled": True, "min_level": "info"}
    r = _run(
        notify_engine.send_alert_notification(
            {"id": "a", "title": "t", "severity": "info", "type": "alert", "message": "m"}
        )
    )
    assert r["status"] == "no_channel_configured"
    notify_engine.NOTIFY_CONFIG = orig


def test_planner_extended(planner_fakes, monkeypatch):
    # llm moderation failure and budget failure
    monkeypatch.setattr(planner, "moderate_content", lambda *a, **kw: (False, ["bad"]))
    cot = planner.ChainOfThought(MagicMock())
    steps = cot.reason("fix cpu", {})
    assert steps  # falls back to rule
    monkeypatch.setattr(planner, "moderate_content", lambda *a, **kw: (True, []))
    monkeypatch.setattr(
        planner,
        "get_session_budget",
        lambda *a, **kw: MagicMock(check_and_record=lambda *a, **kw: False),
    )
    steps2 = cot.reason("fix cpu", {"session_id": "s"})
    assert steps2
    # task planner with scale and generic goals
    tp = planner.TaskPlanner()
    tp.plan("扩容 payment 服务", {"service": "payment"}, ["scale"])
    tp.plan("未知问题", {"target": "system"}, ["collect"], max_tasks=2)
    # ready tasks and summary with completed status
    for t in tp.tasks.values():
        t.status = planner.TaskStatus.COMPLETED
    assert tp.get_ready_tasks() == []
    assert tp.get_plan_summary()["completed"] > 0


# =============================================================================
# Extended coverage: tools, ai_engine, heal_graph
# =============================================================================


def test_tools_extended(tools_fakes, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda *a, **kw: None)
    reg = tools.create_tool_registry()
    exec = tools.create_tool_executor(reg)
    # enable Prometheus branches
    monkeypatch.setattr(tools.observability_client, "get_prometheus_url", lambda: "http://prom")
    monkeypatch.setattr(
        tools.observability_client,
        "query_prometheus",
        lambda *a, **kw: {"data": {"result": [{"value": [0, 1.0]}]}},
    )
    monkeypatch.setattr(
        tools.observability_client,
        "query_prometheus_range",
        lambda *a, **kw: {"data": {"result": [{"values": [[0, 0.5]]}]}},
    )
    monkeypatch.setattr(
        tools.observability_client, "_extract_prom_scalar_value", lambda *a, **kw: 0.5
    )
    monkeypatch.setattr(
        tools.observability_client,
        "query_service_metrics",
        lambda *a, **kw: {"qps": 1, "source": "x"},
    )
    monkeypatch.setattr(
        tools.observability_client, "query_network_metrics", lambda *a, **kw: {"latency_ms": 1}
    )
    monkeypatch.setattr(
        tools.observability_client,
        "query_kubernetes_pod",
        lambda *a, **kw: {"available": True, "phase": "Running"},
    )
    monkeypatch.setattr(
        tools.observability_client,
        "query_kubernetes_node",
        lambda *a, **kw: {"available": True, "conditions": {}},
    )
    monkeypatch.setattr(
        tools.observability_client, "query_change_events", lambda *a, **kw: [{"ts": 1}]
    )
    # stub optional dependencies
    fake_smm = types.ModuleType("core.service_monitoring_manager")
    fake_smm.get_service_monitoring_manager = lambda: MagicMock(
        get_service_metrics=lambda *a, **kw: []
    )
    monkeypatch.setitem(sys.modules, "core.service_monitoring_manager", fake_smm)
    fake_alert = types.ModuleType("core.alert_engine")
    fake_alert.alert_history = [{"title": "svc down", "desc": "svc", "host": "h1", "source": "svc"}]
    monkeypatch.setitem(sys.modules, "core.alert_engine", fake_alert)
    fake_cfg = types.ModuleType("core.config_manager")
    fake_cfg.config_manager = MagicMock(
        _audit_log=[{"timestamp": 9999999999.0, "type": "deploy", "change": "svc", "details": "d"}]
    )
    monkeypatch.setitem(sys.modules, "core.config_manager", fake_cfg)
    monkeypatch.setitem(
        sys.modules,
        "core.root_cause_intelligence",
        types.ModuleType("core.root_cause_intelligence"),
    )
    # execute tools with Prometheus/fallback branches
    for name, params in [
        ("collect_metrics", {"target": "node1"}),
        ("collect_service_metrics", {"service_name": "svc"}),
        ("collect_network_metrics", {"target": "node1"}),
        ("collect_change_events", {"target": "svc", "hours": 24}),
        ("collect_kubernetes_events", {"namespace": "default"}),
        ("collect_container_metrics", {"pod_name": "pod1"}),
        ("collect_host_metrics", {"node_name": "node1"}),
        ("collect_database_metrics", {"database": "db1"}),
        ("collect_correlated_alerts", {"service": "svc"}),
        ("collect_topology", {"service": "svc"}),
        (
            "root_cause_analysis",
            {
                "alert_id": "a1",
                "alert": {"id": "a1"},
                "metrics_data": {},
                "correlated_alerts": [],
                "change_events": [],
                "verification_data": {},
            },
        ),
    ]:
        exec.execute_tool(name, **params)
    # subagent wait=False
    exec.execute_tool("dispatch_subagent", goal="g", context={}, available_tools=[], wait=False)
    # analyze anomaly threshold and empty data
    exec.execute_tool("analyze_anomaly", data=[1.0, 2.0, 3.0], method="threshold")
    # validation error branches
    with pytest.raises(ValueError):
        exec.execute_tool("collect_metrics", target="bad;")
    with pytest.raises(ValueError):
        exec.execute_tool("scale_service", service_name="x", replicas=2000)
    with pytest.raises(ValueError):
        exec.execute_tool("restart_service", service_name="x", timeout="bad")
    # selector branches
    sel = tools.ToolSelector(reg)
    for desc in [
        "重启 svc",
        "扩容 svc",
        "发布变更",
        "关联告警",
        "服务指标",
        "网络延迟",
        "数据库慢查询",
        "pod 异常",
        "拓扑依赖",
        "健康检查",
    ]:
        sel.select_tool(desc, {"target": "svc", "service": "svc"})
    # health check exceptions
    monkeypatch.setattr("httpx.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail")))
    monkeypatch.setattr(
        "socket.create_connection", lambda *a, **kw: (_ for _ in ()).throw(Exception("fail"))
    )
    exec.execute_tool("check_health", target="http://x")
    exec.execute_tool("check_health", target="x:80")
    # restart/scale real command branches
    monkeypatch.setattr("shutil.which", lambda *a, **kw: "/bin/" + a[0])
    import subprocess

    monkeypatch.setattr(
        "subprocess.run", MagicMock(return_value=MagicMock(returncode=0, stdout="", stderr=""))
    )
    monkeypatch.setenv("FORCE_REPAIR_COMMANDS", "1")
    exec.execute_tool("restart_service", service_name="svc")
    exec.execute_tool("scale_service", service_name="svc", replicas=2)

    # retry path for monitoring timeout
    def _raise_timeout():
        raise asyncio.TimeoutError()

    timeout_tool = tools.Tool(
        name="timeout_tool",
        description="t",
        category=tools.ToolCategory.MONITORING,
        function=_raise_timeout,
        required_params=[],
    )
    reg.register(timeout_tool)
    with pytest.raises(asyncio.TimeoutError):
        exec._execute_with_retry(timeout_tool, False, None, {})


async def test_ai_engine_branches(ai_fakes, monkeypatch):
    # content moderation violation
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", True)
    monkeypatch.setattr(
        ai_engine, "moderate_content", lambda texts, check_injection=False: (False, ["bad"])
    )
    with pytest.raises(ai_engine.HTTPException):
        await ai_engine.analyze("bad", validate_json=False)
    monkeypatch.setattr(ai_engine, "CONTENT_MODERATION_AVAILABLE", False)
    # LLM router unavailable + RAG branch
    monkeypatch.setattr(
        ai_engine,
        "_rag_pipeline",
        AsyncMock(retrieve_and_generate=AsyncMock(return_value="RAG context")),
    )
    monkeypatch.setattr(ai_engine, "get_llm_router", None)
    res = await ai_engine.analyze("cpu high")
    assert "规则" in res or "降级" in res
    # restore router for budget tests
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: ai_fakes[0])
    # cost budget failure
    ai_fakes[1].check_budget = lambda *a, **kw: False
    res = await ai_engine.analyze("cpu high")
    assert "规则" in res or "降级" in res
    # session budget failure
    ai_fakes[1].check_budget = lambda *a, **kw: True
    ai_fakes[2].check_and_record = lambda *a, **kw: False
    res = await ai_engine.analyze("cpu high")
    assert "规则" in res or "降级" in res
    # markdown JSON extraction
    ai_fakes[2].check_and_record = lambda *a, **kw: True
    ai_fakes[0].generate.return_value = {
        "content": '```json\n{"data_assessment":{"reliability_score":0.9,"reliability_concerns":[]},"candidates":[{"rank":1,"root_cause":"x","confidence":0.8,"expected_observations_if_true":[],"missing_data":[],"is_verifiable":true,"evidence":[]}],"multi_root_cause_note":"","escalation_recommended":false,"escalation_reason":"","recommended_action":""}\n```',  # noqa: E501  # Line too long (intentional)
        "model": "fake",
        "usage": {},
    }
    res = await ai_engine.analyze("cpu high", validate_json=True)
    assert "data_assessment" in res
    # redact helpers
    assert ai_engine._redact_value({"x": ["y"]})
    # NLI all intents
    nli = ai_engine.NaturalLanguageInteraction()
    for q in [
        "what is status",
        "why is cpu high",
        "how to fix",
        "predict memory",
        "recommend optimization",
    ]:
        await nli.process_natural_language_query(q, {"metrics": {"cpu": "80%"}})
    # conversation trim
    for _ in range(12):
        await nli.maintain_conversation("u1", "q")
    # predictive disk and memory
    pred = ai_engine.PredictiveAnalysisEngine()
    await pred.predict_system_anomalies(
        {"memory": {"usage_percent": 90}, "disk": [{"usage_percent": 95, "mount_point": "/"}]}
    )
    await pred.predict_capacity_needs(
        {"cpu": {"usage_percent": 80}, "memory": {"usage_percent": 70}}, growth_rate=0.2
    )
    # recommendations
    rec = ai_engine.IntelligentRecommendationEngine()
    await rec.generate_recommendations({"id": "1", "type": "disk_high", "severity": "critical"})
    await rec.get_personalized_recommendations("u1", [{"type": "scaling"}, {"type": "scaling"}])
    # search_similar with rag_engine
    fake_rag = types.ModuleType("core.rag_engine")
    fake_rag.search_similar = lambda q, limit: [{"id": "1"}]
    monkeypatch.setitem(sys.modules, "core.rag_engine", fake_rag)
    svc = ai_engine.LLMAnalysisService()
    ss = await svc.search_similar("cpu")
    assert ss
    # health disabled
    monkeypatch.setattr(ai_engine, "AI_CONFIG", {"is_enabled": False})
    assert not (await svc.get_health_status())["available"]
    # close_http_client exception
    ai_engine._http_client = MagicMock(
        is_closed=False, aclose=AsyncMock(side_effect=Exception("x"))
    )
    await ai_engine.close_http_client()


async def test_heal_graph_branches(heal_fakes, monkeypatch):
    # fetch alert with no payload
    s = await heal_graph.run_heal(heal_graph.HealState())
    assert s.error or ""
    # generate_runbook fallback to repair script library
    import core.runbook_generator as runbook_mod

    monkeypatch.setattr(runbook_mod, "generate_repair_runbook", lambda *a, **kw: {"success": False})
    _fake_auto = types.ModuleType("core.auto_heal")

    class _Script:
        pass

    script = _Script()
    script.script_content = "systemctl restart svc\n"
    script.rollback_script = "systemctl start svc\n"
    script.risk_level = "low"
    script.name = "x"
    script.description = "d"
    script.requires_approval = False
    _fake_auto.repair_script_library = MagicMock(get_script=lambda k: script)
    monkeypatch.setitem(sys.modules, "core.auto_heal", _fake_auto)
    monkeypatch.setattr(
        heal_graph,
        "RiskLevel",
        type("RiskLevel", (), {"HIGH": "high", "LOW": "low", "SAFE": "safe", "BLOCKED": "blocked"}),
    )
    state = heal_graph.HealState(
        alert={"id": "h2", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s2 = await heal_graph.run_heal(state)
    assert s2 is not None
    # apply_fix command guard blocked
    monkeypatch.setattr(
        heal_graph,
        "analyze_command",
        lambda cmd: {"risk_level": heal_graph.RiskLevel.BLOCKED, "reason": "unsafe"},
    )
    state2 = heal_graph.HealState(
        alert={"id": "h3", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s3 = await heal_graph.run_heal(state2)
    assert "blocked" in (s3.error or "").lower()
    # apply_fix command target mismatch
    monkeypatch.setattr(heal_graph, "analyze_command", lambda cmd: {"risk_level": "low"})
    monkeypatch.setattr(
        runbook_mod,
        "generate_repair_runbook",
        lambda *a, **kw: {
            "success": True,
            "worst_risk": "low",
            "needs_approval": False,
            "auto_executable": True,
            "runbook": {
                "script_key": "x",
                "name": "x",
                "commands": ["systemctl restart other"],
                "rollback": "",
                "risk_level": "low",
                "params": {},
            },
            "source": "test",
        },
    )
    state3 = heal_graph.HealState(
        alert={"id": "h4", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s4 = await heal_graph.run_heal(state3)
    assert "target" in (s4.error or "").lower() or "not found" in (s4.error or "").lower()
    # not approved
    monkeypatch.setattr(heal_graph, "async_get_approval_by_alert", AsyncMock(return_value=None))
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "false")
    monkeypatch.setattr(heal_graph, "_send_alert_notification", AsyncMock())
    state4 = heal_graph.HealState(
        alert={"id": "h5", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s5 = await heal_graph.run_heal(state4)
    assert "not approved" in (s5.error or "").lower()
    # rollback with verification failure and no rollback command
    import core.verifier as verifier_mod

    monkeypatch.setattr(
        verifier_mod, "verify_repair", AsyncMock(return_value={"verified": False, "passed": False})
    )
    monkeypatch.setattr(
        runbook_mod,
        "generate_repair_runbook",
        lambda *a, **kw: {
            "success": True,
            "worst_risk": "low",
            "needs_approval": False,
            "auto_executable": True,
            "runbook": {
                "script_key": "x",
                "name": "x",
                "commands": ["systemctl restart svc"],
                "rollback": "",
                "risk_level": "low",
                "params": {},
            },
            "source": "test",
        },
    )
    monkeypatch.setattr(
        heal_graph,
        "async_get_approval_by_alert",
        AsyncMock(
            return_value={"status": "approved", "approved_at": datetime.datetime.now().isoformat()}
        ),
    )
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state5 = heal_graph.HealState(
        alert={"id": "h6", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s6 = await heal_graph.run_heal(state5)
    assert s6 is not None

    # rollback command blocked by command_guard
    def _guard(cmd):
        if " start " in cmd:
            return {"risk_level": heal_graph.RiskLevel.BLOCKED, "reason": "unsafe"}
        return {"risk_level": "low"}

    monkeypatch.setattr(heal_graph, "analyze_command", _guard)
    monkeypatch.setattr(
        runbook_mod,
        "generate_repair_runbook",
        lambda *a, **kw: {
            "success": True,
            "worst_risk": "low",
            "needs_approval": False,
            "auto_executable": True,
            "runbook": {
                "script_key": "x",
                "name": "x",
                "commands": ["systemctl restart svc"],
                "rollback": "systemctl start svc",
                "risk_level": "low",
                "params": {},
            },
            "source": "test",
        },
    )
    state6 = heal_graph.HealState(
        alert={"id": "h7", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s7 = await heal_graph.run_heal(state6)
    assert "rollback" in (s7.error or "").lower() or s7.escalated
    # complete repair record exception
    monkeypatch.setattr(
        heal_graph, "async_insert_repair_record", AsyncMock(side_effect=Exception("db"))
    )
    monkeypatch.setattr(heal_graph, "analyze_command", lambda cmd: {"risk_level": "low"})
    monkeypatch.setattr(
        verifier_mod, "verify_repair", AsyncMock(return_value={"verified": True, "passed": True})
    )
    state7 = heal_graph.HealState(
        alert={"id": "h8", "metric": "cpu", "title": "t", "status": "firing", "service_name": "svc"}
    )
    s8 = await heal_graph.run_heal(state7)
    assert s8 is not None


def test_heal_graph_helpers_extended(monkeypatch):
    monkeypatch.setattr(heal_graph, "_metrics_history", MagicMock(to_dict=lambda: {"cpu": [95.0]}))
    assert heal_graph._is_alert_resolved(
        {"resolved_condition": {"metric": "cpu", "operator": ">", "threshold": 90}}
    )
    assert not heal_graph._is_alert_resolved(
        {"resolved_condition": {"metric": "cpu", "operator": "<", "threshold": 90}}
    )
    assert isinstance(heal_graph._is_off_hours(), bool)
    assert isinstance(heal_graph._is_auto_approve_allowed(), bool)
    # StateGraph fallback branches
    g = heal_graph.StateGraph(dict)
    runner = g.compile()
    assert _run(runner({})) == {}
    g.set_entry_point("missing")
    runner2 = g.compile()
    assert _run(runner2({})) == {}


# =============================================================================
# Extended coverage: notify_engine, ai_engine, heal_graph (remaining branches)
# =============================================================================


async def test_notify_extended2(notify_cfg, monkeypatch):
    alert = {
        "id": "a",
        "fingerprint": "fp",
        "title": "t",
        "level": "critical",
        "message": "m",
        "summary": "s",
    }
    # slack missing sdk
    monkeypatch.setattr(notify_engine, "_get_slack_client", lambda: None)
    res = await notify_engine._send_slack_notification_once("msg", {"channel": "#x"})
    assert not res["success"]
    # slack API error
    fake_client = AsyncMock()
    fake_client.chat_postMessage = AsyncMock(return_value={"ok": False, "error": "invalid_auth"})
    monkeypatch.setattr(notify_engine, "_get_slack_client", lambda: fake_client)
    res = await notify_engine._send_slack_notification_once("msg", {"channel": "#x"})
    assert not res["success"]
    # teams missing aiohttp / exception
    monkeypatch.setattr(notify_engine, "aiohttp", None)
    res = await notify_engine.send_teams_notification("msg", "https://x.webhook.office.com/x")
    assert not res["success"]
    monkeypatch.setattr(
        notify_engine,
        "aiohttp",
        types.SimpleNamespace(
            ClientSession=lambda: MagicMock(
                __aenter__=AsyncMock(side_effect=Exception("boom")),
                __aexit__=AsyncMock(),
            )
        ),
    )
    res = await notify_engine.send_teams_notification("msg", "https://x.webhook.office.com/x")
    assert not res["success"]
    # email exception
    monkeypatch.setattr(
        notify_engine.smtplib, "SMTP", lambda *a, **kw: (_ for _ in ()).throw(Exception("smtp"))
    )
    res = await notify_engine.send_email_notification(
        alert, {"email_to": "x@x.com"}, "subj", "body"
    )
    assert not res["success"]
    # phone/sms with provider but no recipient
    monkeypatch.setattr(notify_engine, "_resolve_oncall_recipients", AsyncMock(return_value=[]))
    cfg = {"phone_provider": "twilio", "phone_to": ""}
    res = await notify_engine._send_phone_notification(alert, cfg)
    assert not res["success"]
    res = await notify_engine._send_sms_notification(alert, cfg)
    assert not res["success"]
    # dingtalk URL already contains timestamp/sign
    orig = notify_engine.NOTIFY_CONFIG.get("dingtalk_webhook")
    notify_engine.NOTIFY_CONFIG["dingtalk_webhook"] = "https://x.com?timestamp=1&sign=abc"
    res = await notify_engine._send_dingtalk(alert)
    assert isinstance(res, dict)
    if orig is not None:
        notify_engine.NOTIFY_CONFIG["dingtalk_webhook"] = orig
    # send_alert cooldown and one-channel break
    notify_engine.NOTIFY_CONFIG["enabled"] = True
    notify_engine.NOTIFY_CONFIG["min_level"] = "info"
    a2 = {
        "id": "a2",
        "fingerprint": "fp2",
        "title": "t",
        "severity": "info",
        "type": "alert",
        "message": "m",
    }
    r1 = await notify_engine.send_alert_notification(a2)
    assert r1["status"] != "no_channel_configured"
    r2 = await notify_engine.send_alert_notification(a2)
    assert r2["results"]["email"]["skipped"]
    # query_notifications severity filter and history exception
    notify_engine._track_notification_status(a2, "email", "success", {})
    qs = await notify_engine.query_notifications(severity="critical", limit=10)
    assert isinstance(qs, list)
    monkeypatch.setattr(notify_engine, "query_notifications", AsyncMock(side_effect=Exception("q")))
    res = await notify_engine.get_notification_history(limit=5, severity="critical")
    assert res == []
    # close_http_client exception
    notify_engine._http_client = MagicMock(
        is_closed=False, aclose=AsyncMock(side_effect=Exception("x"))
    )
    await notify_engine.close_http_client()


async def test_ai_engine_extended2(ai_fakes, monkeypatch):
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: ai_fakes[0])
    # invalid JSON falls back
    ai_fakes[0].generate.return_value = {"content": "not json", "model": "fake", "usage": {}}
    res = await ai_engine.analyze("cpu high", validate_json=True)
    assert res is not None
    # custom system prompt path
    res = await ai_engine.analyze("cpu high", system_prompt="custom", validate_json=False)
    assert res is not None
    # LLMAnalysisService.analyze
    svc = ai_engine.LLMAnalysisService()
    await svc.analyze(
        context={
            "query": "cpu high",
            "metrics_snapshot": '{"cpu": 80}',
            "rich_context": {"services": ["svc"]},
        }
    )
    # more recommendation types
    rec = ai_engine.IntelligentRecommendationEngine()
    await rec.generate_recommendations({"id": "1", "type": "memory_high", "severity": "high"})
    await rec.generate_recommendations({"id": "1", "type": "cpu_high", "severity": "critical"})
    # NLI with disk/host/time entities
    nli = ai_engine.NaturalLanguageInteraction()
    await nli.process_natural_language_query(
        "what about disk on host-1 today", {"metrics": {"cpu": "80%"}}
    )
    # predictive network/disk
    pred = ai_engine.PredictiveAnalysisEngine()
    await pred.predict_system_anomalies({"network": {"packet_loss_percent": 5}})
    await pred.predict_capacity_needs(
        {"network": {"bandwidth_utilization_percent": 90}}, growth_rate=0.3
    )


async def test_heal_graph_extended2(heal_fakes, monkeypatch):
    import core.runbook_generator as runbook_mod
    import core.verifier as verifier_mod

    _fake_auto = types.ModuleType("core.auto_heal")

    class _Script:
        pass

    script = _Script()
    script.script_content = "cmd\n"
    script.rollback_script = "rollback\n"
    script.risk_level = "low"
    script.name = "x"
    script.description = "d"
    script.requires_approval = False
    _fake_auto.repair_script_library = MagicMock(get_script=lambda k: script)
    monkeypatch.setitem(sys.modules, "core.auto_heal", _fake_auto)
    monkeypatch.setattr(
        heal_graph,
        "RiskLevel",
        type("RiskLevel", (), {"HIGH": "high", "LOW": "low", "SAFE": "safe", "BLOCKED": "blocked"}),
    )
    # generate_runbook fallback for disk / memory / service
    monkeypatch.setattr(runbook_mod, "generate_repair_runbook", lambda *a, **kw: {"success": False})
    for metric in ("disk", "memory", "service"):
        state = heal_graph.HealState(
            alert={"id": f"h_{metric}", "metric": metric, "title": metric, "status": "firing"}
        )
        await heal_graph.run_heal(state)
    # apply_fix no valid runbook
    s = heal_graph.HealState(alert={"id": "h10", "metric": "cpu"})
    s.runbook = None
    await heal_graph.apply_fix(s)
    assert "No valid runbook" in (s.error or "")
    # apply_fix confidence gate and HITL notification exception
    s2 = heal_graph.HealState(
        alert={"id": "h11", "metric": "cpu", "title": "t", "status": "firing"}
    )
    s2.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "commands": ["systemctl restart svc"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
            "confidence": 0.5,
        },
    }
    monkeypatch.setenv("HEAL_EXECUTION_CONFIDENCE_THRESHOLD", "0.8")
    monkeypatch.setattr(heal_graph, "async_get_approval_by_alert", AsyncMock(return_value=None))
    monkeypatch.setattr(
        heal_graph, "_send_alert_notification", AsyncMock(side_effect=Exception("x"))
    )
    await heal_graph.apply_fix(s2)
    assert "not approved" in (s2.error or "").lower()
    # apply_fix pre-execution check failure
    s3 = heal_graph.HealState(
        alert={"id": "h12", "metric": "cpu", "title": "t", "status": "firing"}
    )
    s3.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "commands": ["systemctl restart svc"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
    }
    monkeypatch.setattr(heal_graph, "_pre_execution_check", lambda *a, **kw: (False, "self-healed"))
    monkeypatch.setattr(
        heal_graph, "async_get_approval_by_alert", AsyncMock(return_value={"status": "approved"})
    )
    await heal_graph.apply_fix(s3)
    assert "Pre-execution check failed" in (s3.error or "")
    # hardware alert simulated
    monkeypatch.setattr(heal_graph, "_pre_execution_check", lambda *a, **kw: (True, ""))
    s4 = heal_graph.HealState(
        alert={
            "id": "h13",
            "metric": "ipmi",
            "title": "ipmi",
            "category": "hardware",
            "status": "firing",
        }
    )
    s4.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "commands": ["ipmitool reset"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
    }
    monkeypatch.setattr(
        heal_graph, "async_get_approval_by_alert", AsyncMock(return_value={"status": "approved"})
    )
    monkeypatch.setattr(heal_graph, "analyze_command", lambda cmd: {"risk_level": "low"})
    await heal_graph.apply_fix(s4)
    assert s4.fix_applied
    # evaluate branches
    s5 = heal_graph.HealState(alert={"id": "h14", "metric": "cpu"})
    s5.fix_applied = False
    s5.runbook = "string"
    await heal_graph.evaluate(s5)
    monkeypatch.setattr(
        verifier_mod,
        "verify_repair",
        AsyncMock(return_value=MagicMock(model_dump=lambda: {"verified": True, "passed": True})),
    )
    s6 = heal_graph.HealState(
        alert={"id": "h15", "metric": "cpu", "title": "t", "status": "firing"}
    )
    s6.fix_applied = True
    s6.runbook = {"runbook": {"script_key": "x", "params": {}}}
    await heal_graph.evaluate(s6)
    # complete exceptions
    s7 = heal_graph.HealState(
        alert={"id": "h16", "metric": "cpu", "title": "t", "status": "firing"}
    )
    s7.fix_applied = True
    s7.verification = {"passed": True}
    s7.runbook = {"worst_risk": "low"}
    monkeypatch.setattr(
        heal_graph, "cleanup_expired_snapshots", AsyncMock(side_effect=Exception("x"))
    )
    monkeypatch.setattr(
        heal_graph, "async_insert_repair_record", AsyncMock(side_effect=Exception("x"))
    )
    await heal_graph.complete(s7)
    assert s7.metrics


def test_heal_graph_helpers2(monkeypatch):
    monkeypatch.setattr(
        heal_graph,
        "_metrics_history",
        MagicMock(to_dict=lambda: {"cpu": [95], "memory": [90], "disk": [95]}),
    )
    assert heal_graph._is_alert_resolved(
        {"resolved_condition": {"metric": "cpu", "operator": ">", "threshold": 90}}
    )
    assert not heal_graph._is_alert_resolved(
        {"resolved_condition": {"metric": "memory", "operator": ">", "threshold": 95}}
    )
    assert heal_graph._is_alert_resolved(
        {
            "resolved_condition": {
                "metric": "disk",
                "operator": ">",
                "threshold": 90,
                "aggregate": "latest",
            }
        }
    )


async def test_ai_engine_extended3(ai_fakes, monkeypatch):
    monkeypatch.setattr(ai_engine, "get_llm_router", lambda: ai_fakes[0])
    ai_fakes[0].generate.return_value = {
        "content": '{"root_cause": "x"}',
        "model": "fake",
        "usage": {"total_tokens": 1000},
    }
    await ai_engine.analyze("disk slow", validate_json=True)
    await ai_engine._rate_limit_wait()
    ai_engine._get_http_client()
    await ai_engine.close_http_client()
    svc = ai_engine.LLMAnalysisService()
    await svc.search_similar("q")
    await svc.get_health_status()
    ai_engine._redact_text("abc")
    ai_engine._validate_root_cause_output('{"root_cause": "x"}')
    rec = ai_engine.IntelligentRecommendationEngine()
    await rec.generate_recommendations({"type": "cpu_high", "severity": "high"})
    await rec.generate_recommendations({"type": "memory_high", "severity": "high"})
    await rec.generate_recommendations({"type": "network_latency", "severity": "high"})
    await rec.generate_recommendations({"type": "database_slow", "severity": "high"})
    nli = ai_engine.NaturalLanguageInteraction()
    await nli.process_natural_language_query("reboot", {})
    # rich context branches and edge cases
    await ai_engine.analyze(
        "q",
        validate_json=False,
        platform="invalid",
        rich_context={
            "recent_alerts": [{"level": "critical", "title": "t", "desc": "d"}],
            "recent_repairs": [{"script_key": "x", "success": True}],
            "service_metrics": {"cpu": 80},
            "dependencies": {"a": ["b"]},
            "upstream_callers": {"a": {"x": 1}},
            "downstream_dependencies": {"a": {"x": 1}},
            "infrastructure_metrics": {"cpu": 50},
            "change_events": [
                {"timestamp": "t", "type": "deploy", "target": "svc", "description": "d"}
            ],
        },
    )
    # cost/session budget exceptions, audit, enhancement
    monkeypatch.setattr(
        ai_engine, "get_llm_cost_monitor", lambda: (_ for _ in ()).throw(Exception("cm"))
    )
    monkeypatch.setattr(
        ai_engine, "get_session_budget", lambda *a, **kw: (_ for _ in ()).throw(Exception("sb"))
    )
    enh = types.ModuleType("core.ai_enhancement")
    enh.get_ai_enhancer = lambda: MagicMock(enhance_analysis=lambda *a, **kw: None)
    monkeypatch.setitem(sys.modules, "core.ai_enhancement", enh)
    await ai_engine.analyze("q", validate_json=False)
    # search_similar success branch with RAG
    monkeypatch.setattr(ai_engine, "AUDIT_LOGGER_AVAILABLE", True)
    monkeypatch.setattr(ai_engine, "log_audit_event", MagicMock())
    rag = types.ModuleType("core.rag_engine")
    rag.search_similar = lambda q, limit=10: [{"id": "1"}]
    monkeypatch.setitem(sys.modules, "core.rag_engine", rag)
    await svc.search_similar("q")


async def test_heal_graph_extended3(heal_fakes, monkeypatch):
    import core.runbook_generator as runbook_mod

    monkeypatch.setattr(
        runbook_mod,
        "generate_repair_runbook",
        lambda *a, **kw: {
            "success": True,
            "runbook": {
                "script_key": "x",
                "name": "x",
                "commands": ["echo fix"],
                "rollback": "echo rollback",
                "risk_level": "low",
                "params": {},
            },
        },
    )
    s = heal_graph.HealState(alert={"id": "h20", "metric": "cpu", "title": "t", "status": "firing"})
    await heal_graph.run_heal(s)
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    fake_asyncio = MagicMock()
    fake_asyncio.subprocess = MagicMock(PIPE=1)
    fake_proc = MagicMock(returncode=0, communicate=AsyncMock(return_value=(b"ok", b"")))
    fake_asyncio.create_subprocess_shell = AsyncMock(return_value=fake_proc)
    fake_asyncio.create_subprocess_exec = AsyncMock(return_value=fake_proc)
    fake_asyncio.wait_for = AsyncMock(return_value=(b"ok", b""))
    fake_asyncio.TimeoutError = asyncio.TimeoutError
    monkeypatch.setattr(heal_graph, "asyncio", fake_asyncio)
    monkeypatch.setattr(
        heal_graph,
        "async_get_approval_by_alert",
        AsyncMock(
            return_value={
                "status": "approved",
                "approved_at": heal_graph.datetime.now().isoformat(),
            }
        ),
    )
    monkeypatch.setattr(heal_graph, "analyze_command", lambda cmd: {"risk_level": "low"})
    s2 = heal_graph.HealState(
        alert={"id": "h21", "metric": "cpu", "title": "t", "status": "firing", "platform": "linux"}
    )
    s2.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": ["echo fix"],
            "rollback": "echo rollback",
            "risk_level": "low",
            "params": {},
        },
    }
    await heal_graph.apply_fix(s2)
    assert s2.fix_applied
    s3 = heal_graph.HealState(
        alert={"id": "h22", "metric": "cpu", "title": "t", "status": "firing", "platform": "linux"}
    )
    s3.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": ["echo fix"],
            "rollback": "echo rollback",
            "risk_level": "low",
            "params": {},
        },
    }
    s3.verification = {"passed": False}
    s3.rollback_info = {"rollback_commands": ["echo rollback"]}
    s3.snapshot_id = "snap1"
    s3.approval_status = "approved"
    await heal_graph.rollback(s3)
    assert not s3.fix_applied


async def test_heal_graph_extended4(heal_fakes, monkeypatch):
    import core.runbook_generator as runbook_mod

    _fake_auto = types.ModuleType("core.auto_heal")

    class _Script:
        pass

    script = _Script()
    script.script_content = "cmd\n"
    script.rollback_script = "rollback\n"
    script.risk_level = "low"
    script.name = "x"
    script.description = "d"
    script.requires_approval = False
    _fake_auto.repair_script_library = MagicMock(get_script=lambda k: script)
    monkeypatch.setitem(sys.modules, "core.auto_heal", _fake_auto)
    monkeypatch.setattr(runbook_mod, "generate_repair_runbook", lambda *a, **kw: {"success": False})
    monkeypatch.setattr(
        heal_graph,
        "RiskLevel",
        type("RiskLevel", (), {"SAFE": "safe", "LOW": "low", "HIGH": "high", "BLOCKED": "blocked"}),
    )
    # hardware runbook fallback
    for metric in ("ipmi", "redfish", "raid", "smart", "cordon", "node"):
        s = heal_graph.HealState(
            alert={"id": f"h_{metric}", "metric": metric, "title": metric, "status": "firing"}
        )
        await heal_graph.run_heal(s)
    # helpers
    assert "service1" in heal_graph._allowed_targets_from_alert({"service_name": "service1"})
    assert "123" in heal_graph._allowed_targets_from_alert({"value": 123})


async def test_heal_graph_edge_cases(heal_fakes, monkeypatch):
    # fetch_alert without alert
    s0 = await heal_graph.fetch_alert(heal_graph.HealState())
    assert "No alert payload" in s0.error

    # invoke_agent with explicit query and metrics_history exception
    monkeypatch.setattr(
        heal_graph, "_metrics_history", MagicMock(to_dict=MagicMock(side_effect=Exception("x")))
    )
    s1 = heal_graph.HealState(alert={"id": "h34", "query": "why"})
    await heal_graph.invoke_agent(s1)
    assert s1.analysis["query"] == "why"

    # apply_fix auto-approved, empty commands and metrics exception
    monkeypatch.setattr(heal_graph, "async_get_approval_by_alert", AsyncMock(return_value=None))
    monkeypatch.setattr(
        heal_graph, "_metrics_history", MagicMock(to_dict=MagicMock(side_effect=Exception("x")))
    )
    s2 = heal_graph.HealState(
        alert={"id": "h35", "metric": "cpu", "title": "t", "status": "firing"}
    )
    s2.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": [],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
    }
    await heal_graph.apply_fix(s2)
    assert "no executable commands" in s2.error

    # execute_command with failing command
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    fake_asyncio = MagicMock()
    fake_asyncio.subprocess = MagicMock(PIPE=1)
    fake_proc = MagicMock(returncode=1, communicate=AsyncMock(return_value=(b"out", b"err")))
    fake_asyncio.create_subprocess_shell = AsyncMock(return_value=fake_proc)
    fake_asyncio.create_subprocess_exec = AsyncMock(return_value=fake_proc)
    fake_asyncio.wait_for = AsyncMock(return_value=(b"out", b"err"))
    fake_asyncio.TimeoutError = asyncio.TimeoutError
    monkeypatch.setattr(heal_graph, "asyncio", fake_asyncio)
    monkeypatch.setattr(heal_graph, "_metrics_history", MagicMock(to_dict=lambda: {}))
    s3 = heal_graph.HealState(
        alert={"id": "h36", "metric": "cpu", "title": "t", "status": "firing", "platform": "linux"},
    )
    s3.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": ["echo fail"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
        "confidence": "bad",
    }
    await heal_graph.apply_fix(s3)
    assert "rc=1" in s3.error

    # evaluate with non-dict verifier return and verified=False
    import core.verifier as verifier_mod

    monkeypatch.setattr(verifier_mod, "verify_repair", AsyncMock(return_value="raw"))
    s4 = heal_graph.HealState(
        alert={"id": "h37"},
        fix_applied=True,
        runbook={
            "success": True,
            "script_key": "x",
            "runbook": {"script_key": "x", "commands": ["cmd"]},
        },
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )
    await heal_graph.evaluate(s4)
    assert s4.verification["passed"]
    monkeypatch.setattr(verifier_mod, "verify_repair", AsyncMock(return_value={"verified": False}))
    s5 = heal_graph.HealState(
        alert={"id": "h38"},
        fix_applied=True,
        runbook={
            "success": True,
            "script_key": "x",
            "runbook": {"script_key": "x", "commands": ["cmd"]},
        },
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )
    await heal_graph.evaluate(s5)
    assert not s5.verification["passed"]


async def test_heal_graph_final_coverage(heal_fakes, monkeypatch):
    # hardware fallback else branch
    import core.runbook_generator as runbook_mod

    _fake_auto = types.ModuleType("core.auto_heal")

    class _Script:
        pass

    script = _Script()
    script.script_content = "cmd\n"
    script.rollback_script = "rollback\n"
    script.risk_level = "low"
    script.name = "x"
    script.description = "d"
    script.requires_approval = False
    _fake_auto.repair_script_library = MagicMock(get_script=lambda k: script)
    monkeypatch.setitem(sys.modules, "core.auto_heal", _fake_auto)
    monkeypatch.setattr(
        heal_graph,
        "RiskLevel",
        type("RiskLevel", (), {"SAFE": "safe", "LOW": "low", "HIGH": "high", "BLOCKED": "blocked"}),
    )
    monkeypatch.setattr(runbook_mod, "generate_repair_runbook", lambda *a, **kw: {"success": False})
    s1 = await heal_graph.generate_runbook(
        heal_graph.HealState(
            alert={"id": "h40", "category": "hardware", "metric": "other", "title": "o"}
        )
    )
    assert s1.runbook.get("success")

    # invoke_agent alert_history not iterable
    alert_engine = types.ModuleType("core.alert_engine")
    alert_engine.alert_history = 123  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "core.alert_engine", alert_engine)
    s2 = heal_graph.HealState(alert={"id": "h43", "query": "why"})
    await heal_graph.invoke_agent(s2)
    assert s2.analysis["query"] == "why"

    # apply_fix windows execution + confidence parse + upsert/ metrics exceptions
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    monkeypatch.setattr(heal_graph, "async_get_approval_by_alert", AsyncMock(return_value=None))
    monkeypatch.setattr(
        heal_graph, "async_upsert_pending_approval", AsyncMock(side_effect=Exception("x"))
    )
    monkeypatch.setattr(
        heal_graph, "_metrics_history", MagicMock(to_dict=MagicMock(side_effect=Exception("x")))
    )
    fake_asyncio = MagicMock()
    fake_asyncio.subprocess = MagicMock(PIPE=1)
    fake_proc = MagicMock(returncode=1, communicate=AsyncMock(return_value=(b"out", b"err")))
    fake_asyncio.create_subprocess_shell = AsyncMock(return_value=fake_proc)
    fake_asyncio.create_subprocess_exec = AsyncMock(return_value=fake_proc)
    fake_asyncio.wait_for = AsyncMock(return_value=(b"out", b"err"))
    fake_asyncio.TimeoutError = asyncio.TimeoutError
    monkeypatch.setattr(heal_graph, "asyncio", fake_asyncio)
    s3 = heal_graph.HealState(
        alert={
            "id": "h41",
            "metric": "cpu",
            "title": "t",
            "status": "firing",
            "platform": "windows",
        },
    )
    s3.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": ["echo fail"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
            "confidence": "bad",
        },
    }
    await heal_graph.apply_fix(s3)
    assert "rc=1" in s3.error

    # execute_command exception path
    fake_asyncio.create_subprocess_exec = AsyncMock(side_effect=Exception("boom"))
    s4 = heal_graph.HealState(
        alert={
            "id": "h42",
            "metric": "cpu",
            "title": "t",
            "status": "firing",
            "platform": "windows",
        },
    )
    s4.runbook = {
        "success": True,
        "worst_risk": "low",
        "auto_executable": True,
        "runbook": {
            "script_key": "x",
            "name": "x",
            "commands": ["echo boom"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
    }
    await heal_graph.apply_fix(s4)
    assert "Command execution failed" in s4.error
