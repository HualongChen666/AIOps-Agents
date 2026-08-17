# -*- coding: utf-8 -*-
"""Targeted functional coverage tests for core.team_collaboration_engine,
core.ai.llm_router.enhanced_router, core.k8s_repair, core.alert_service
and core.alert_providers.prometheus.
"""

import asyncio
import json
import sys
import types
from collections import deque
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.ai.llm_router.enhanced_router as enhanced_router
import core.alert_providers.prometheus as prom
import core.alert_service as alert_service_mod
import core.k8s_repair as k8s_repair
import core.query_optimization as qo
import core.team_collaboration_engine as tce
from core.ai.llm_router.capability_evaluator import TaskType
from core.alert_providers.base import get_alert_provider
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.core]


# -----------------------------------------------------------------------------
# core.team_collaboration_engine
# -----------------------------------------------------------------------------
@pytest.fixture
def tce_tmp(monkeypatch, tmp_path):
    """Point team collaboration persistence to a temp directory."""
    monkeypatch.setattr(tce, "DATA_DIR", tmp_path)
    monkeypatch.setattr(tce, "TEAMS_FILE", tmp_path / "teams.json")
    return tmp_path


def _write_teams(data):
    tce.TEAMS_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.mark.asyncio
async def test_tce_seed_and_list(tce_tmp):
    teams = await tce.list_teams()
    assert len(teams) == 1
    assert teams[0]["id"] == "T-001"


@pytest.mark.asyncio
async def test_tce_oncall_future_and_missing(tce_tmp):
    oncall = await tce.get_team_oncall("T-001", datetime(2026, 1, 20, tzinfo=timezone.utc))
    assert oncall["team_id"] == "T-001"
    assert oncall["primary"]["user_id"] in oncall["primary"] or oncall["primary"]
    assert oncall["next_rotation_in_hours"] >= 0
    assert oncall["rotation_type"] == "weekly"

    with pytest.raises(ValueError, match="Team 'missing' not found"):
        await tce.get_team_oncall("missing")


@pytest.mark.asyncio
async def test_tce_oncall_before_start(tce_tmp):
    oncall = await tce.get_team_oncall("T-001", datetime(2025, 12, 31, tzinfo=timezone.utc))
    assert oncall["primary"]["user_id"] == "U-001"


@pytest.mark.asyncio
async def test_tce_handoff_workflow(tce_tmp):
    h = await tce.create_handoff("T-001", "U-001", "U-002", "deploy done")
    assert h["from_user_id"] == "U-001"
    assert h["to_user_id"] == "U-002"
    assert h["team_id"] == "T-001"

    system_h = await tce.create_handoff("T-001", None, None, "system note")
    assert system_h["from_user_id"] == "system"

    with pytest.raises(ValueError, match="From user 'not-member' is not a team member"):
        await tce.create_handoff("T-001", "not-member", "U-002", "bad")

    with pytest.raises(ValueError, match="To user 'bad' is not a team member"):
        await tce.create_handoff("T-001", "U-001", "bad", "bad")

    handoffs = await tce.list_handoffs("T-001")
    assert len(handoffs) == 2


@pytest.mark.asyncio
async def test_tce_escalation_workflow(tce_tmp):
    e1 = await tce.escalate_incident("INC-1", "T-001", "no response")
    assert e1["level"] == 1
    assert e1["status"] == "escalated"
    assert e1["notified_user_id"] == "U-001"

    e2 = await tce.escalate_incident("INC-1", "T-001")
    assert e2["level"] == 2
    assert e2["notified_user_id"] == "U-002"

    e3 = await tce.escalate_incident("INC-1", "T-001")
    assert e3["level"] == 3
    assert e3["notified_user_id"] == "U-001"

    with pytest.raises(ValueError, match="Maximum escalation level reached"):
        await tce.escalate_incident("INC-1", "T-001")


@pytest.mark.asyncio
async def test_tce_dashboards_and_empty_rotation(tce_tmp):
    data = tce._seed_data()
    data["shared_dashboards"] = [
        {"id": "D-1", "team_id": "T-001", "name": "k8s"},
        {"id": "D-2", "team_id": "T-002", "name": "cloud"},
    ]
    data["teams"].append(
        {
            "id": "T-EMPTY",
            "members": [{"user_id": "U-X"}],
            "rotation": {"type": "weekly", "start_date": "2026-01-01T00:00:00+00:00", "order": []},
            "escalation_policy": {
                "levels": [
                    {
                        "level": 1,
                        "delay_minutes": 5,
                        "contact_methods": ["email"],
                        "notify_role": "primary",
                    }
                ]
            },
        }
    )
    _write_teams(data)

    dashboards = await tce.list_dashboards("T-001")
    assert len(dashboards) == 1
    assert dashboards[0]["name"] == "k8s"

    all_dash = await tce.list_dashboards()
    assert len(all_dash) == 2

    oncall = await tce.get_team_oncall("T-EMPTY")
    assert oncall["primary"] is None

    esc = await tce.escalate_incident("INC-EMPTY", "T-EMPTY")
    assert esc["level"] == 1
    assert esc["notified_user_id"] == "U-X"
    assert esc["notified_user"]["user_id"] == "U-X"


@pytest.mark.asyncio
async def test_tce_persist_roundtrip(tce_tmp):
    await tce.create_handoff("T-001", "U-001", "U-003", "notes")
    data = json.loads(tce.TEAMS_FILE.read_text(encoding="utf-8"))
    assert len(data["handoffs"]) == 1
    assert data["incidents"] == {}


# -----------------------------------------------------------------------------
# core.ai.llm_router.enhanced_router
# -----------------------------------------------------------------------------
MODEL_CFGS = [
    {
        "model": "gpt-4o-mini",
        "max_tokens": 128000,
        "context_window": 128000,
        "cost_per_1k": 0.015,
    },
    {
        "model": "gpt-3.5-turbo",
        "max_tokens": 16384,
        "context_window": 16384,
        "cost_per_1k": 0.005,
    },
]


def _install_fake_openai(monkeypatch):
    """Install a deterministic openai module with AsyncOpenAI."""
    fake_openai = types.ModuleType("openai")

    class _FakeChoice:
        message = SimpleNamespace(content="AI generated analysis result")

    class _FakeUsage:
        def model_dump(self):
            return {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6}

    class _FakeResponse:
        choices = [_FakeChoice]
        usage = _FakeUsage()

    class _FakeCompletions:
        async def create(self, **kwargs):
            return _FakeResponse()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeAsyncOpenAI:
        def __init__(self, *a, **k):
            self.chat = _FakeChat()

    fake_openai.AsyncOpenAI = _FakeAsyncOpenAI
    monkeypatch.setitem(sys.modules, "openai", fake_openai)


@pytest.mark.asyncio
async def test_router_cost_optimized_and_forced():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="cost_optimized")
    decision = await router.route_request("short prompt")
    assert decision.model_name == "gpt-3.5-turbo"
    assert decision.confidence >= 0.5

    forced = await router.route_request("prompt", force_model="gpt-4o-mini")
    assert forced.model_name == "gpt-4o-mini"
    assert forced.confidence == 1.0


@pytest.mark.asyncio
async def test_router_capability_first_and_balanced():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="capability_first")
    decision = await router.route_request("prompt", task_type=TaskType.ANALYSIS)
    assert decision.model_name == "gpt-4o-mini"
    assert "capability" in decision.reason

    balanced = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="balanced")
    bdecision = await balanced.route_request("prompt", task_type=TaskType.GENERAL)
    assert bdecision.model_name in ("gpt-4o-mini", "gpt-3.5-turbo")


@pytest.mark.asyncio
async def test_router_unknown_strategy_fallback():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="unknown")
    decision = await router.route_request("prompt")
    assert decision.model_name == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_router_forced_unavailable_falls_back(monkeypatch):
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="cost_optimized")
    for _ in range(5):
        router.record_failure("gpt-4o-mini", "timeout")
    assert router._is_model_available("gpt-4o-mini") is False

    decision = await router.route_request("prompt", force_model="gpt-4o-mini")
    assert decision.model_name == "gpt-3.5-turbo"


@pytest.mark.asyncio
async def test_router_no_models_raises():
    router = enhanced_router.EnhancedLLMRouter([], strategy="cost_optimized")
    with pytest.raises(ValueError, match="No models available for routing"):
        await router.route_request("prompt")


@pytest.mark.asyncio
async def test_router_generate_no_key_fallback():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS)
    result = await router.generate("What is the issue?")
    assert result["content"].startswith("[AI Router fallback]")
    assert "model" in result
    assert "usage" in result


@pytest.mark.asyncio
async def test_router_generate_success(monkeypatch):
    _install_fake_openai(monkeypatch)
    monkeypatch.setenv("AI_API_KEY", "test-key")
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS)
    result = await router.generate("analyze", system="sre", max_new_tokens=20)
    assert result["content"] == "AI generated analysis result"
    assert result["model"] == "gpt-3.5-turbo"
    assert result["usage"]["total_tokens"] == 6


@pytest.mark.asyncio
async def test_router_generate_budget_exceeded():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, budget_per_request=0.0)
    result = await router.generate("analyze")
    assert result["content"].startswith("[AI Router fallback]")


@pytest.mark.asyncio
async def test_router_generate_context_window_fallback():
    tiny = [{"model": "tiny", "max_tokens": 2, "context_window": 2, "cost_per_1k": 0.001}]
    router = enhanced_router.EnhancedLLMRouter(tiny)
    result = await router.generate("This is a very long prompt that exceeds tiny context")
    assert result["content"].startswith("[AI Router fallback]")


def test_router_stats_and_record():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS)
    router.record_success("gpt-4o-mini", latency=0.1, actual_cost=0.01)
    router.record_failure("gpt-3.5-turbo", "error")
    stats = router.get_router_stats()
    assert "model_stats" in stats
    assert "circuit_states" in stats
    assert "cost_stats" in stats


# -----------------------------------------------------------------------------
# core.k8s_repair
# -----------------------------------------------------------------------------
@pytest.fixture
def k8s_mocks(monkeypatch):
    """Neutralize external K8s/command dependencies."""
    fake_runner = MagicMock()

    def _fake_run(*args, **kwargs):
        cmd = args[0]
        if cmd and cmd[0] == "/bin/kubectl":
            pod = {
                "metadata": {"ownerReferences": [{"controller": True, "kind": "Deployment"}]},
                "spec": {"volumes": []},
            }
            return SimpleNamespace(returncode=0, stdout=json.dumps(pod), stderr="")
        return SimpleNamespace(returncode=0, stdout="restarted", stderr="")

    fake_runner.run = _fake_run
    monkeypatch.setattr(k8s_repair, "subprocess_runner", fake_runner)
    monkeypatch.setattr(k8s_repair, "shutil", SimpleNamespace(which=lambda name: f"/bin/{name}"))
    monkeypatch.setattr(k8s_repair, "analyze_command", lambda cmd: RiskLevel.SAFE)
    monkeypatch.setattr(k8s_repair, "record_audit", lambda *a, **k: None)
    monkeypatch.setattr(k8s_repair, "record_repair", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(k8s_repair, "push_to_loki", lambda *a, **k: None)
    monkeypatch.setattr(k8s_repair, "register_self_pid", lambda: None)
    k8s_repair._repair_history.clear()
    return fake_runner


def test_k8s_sanitize_and_render():
    assert k8s_repair._sanitize_param("pod-1") == "pod-1"
    assert k8s_repair._sanitize_param(3) == "3"

    with pytest.raises(ValueError, match="max length"):
        k8s_repair._sanitize_param("x" * 200)

    with pytest.raises(ValueError, match="dangerous"):
        k8s_repair._sanitize_param("foo&bar")

    with pytest.raises(ValueError, match="invalid characters"):
        k8s_repair._sanitize_param("foo bar")

    rendered = k8s_repair._render_command(
        "kubectl delete pod {pod} -n {namespace}",
        {"namespace": "default", "pod": "web-0"},
    )
    assert rendered == "kubectl delete pod web-0 -n default"


@pytest.mark.asyncio
async def test_k8s_restart_success(k8s_mocks):
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert result["result"] is True
    assert result["output"] == "restarted"
    assert result["host"] == "k8s-1"


@pytest.mark.asyncio
async def test_k8s_scale_failure(k8s_mocks):
    k8s_repair.subprocess_runner.run = MagicMock(
        return_value=SimpleNamespace(returncode=1, stdout="", stderr="not enough quota")
    )
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"},
        "scale_deployment",
        {"namespace": "default", "deployment": "api", "replicas": 10},
    )
    assert result["result"] is False
    assert result["error"] == "not enough quota"


@pytest.mark.asyncio
async def test_k8s_delete_pod_stateful(k8s_mocks, monkeypatch):
    monkeypatch.setattr(
        k8s_repair,
        "_inspect_pod_state",
        lambda namespace, pod: {"owner_kind": "StatefulSet", "has_pvc": False},
    )
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "delete_pod", {"namespace": "default", "pod": "db-0"}
    )
    assert result["blocked"] is True
    assert "Refusing" in result["error"]

    monkeypatch.setattr(
        k8s_repair,
        "_inspect_pod_state",
        lambda namespace, pod: {"owner_kind": "Deployment", "has_pvc": True},
    )
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "delete_pod", {"namespace": "default", "pod": "cache-0"}
    )
    assert result["blocked"] is True
    assert "has_pvc" in result["error"]


@pytest.mark.asyncio
async def test_k8s_blocked_by_guard(k8s_mocks):
    monkeypatch = k8s_mocks[0] if isinstance(k8s_mocks[0], object) else None  # placeholder
    # Guard patched in fixture; override to BLOCKED
    import unittest.mock

    with unittest.mock.patch.object(k8s_repair, "analyze_command", lambda cmd: RiskLevel.BLOCKED):
        result = await k8s_repair.execute_repair(
            {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
        )
    assert result["blocked"] is True
    assert "blocked" in result["error"].lower()


@pytest.mark.asyncio
async def test_k8s_unknown_script():
    with pytest.raises(ValueError, match="Unknown repair script"):
        await k8s_repair.execute_repair({"host": "k8s-1"}, "missing", {})


def test_k8s_repair_sync(k8s_mocks):
    result = k8s_repair.execute_repair_sync(
        {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert result["result"] is True


@pytest.mark.asyncio
async def test_k8s_repair_all(k8s_mocks, monkeypatch):
    monkeypatch.setattr(
        k8s_repair,
        "K8S_HOSTS",
        [{"host": "k8s-1"}, {"host": "k8s-2"}],
    )
    results = await k8s_repair.repair_all_k8s(
        "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert len(results) == 2
    assert all(r["result"] for r in results)


def test_k8s_inspect_pod_state():
    result = k8s_repair._inspect_pod_state("default", "pod-1")
    assert "owner_kind" in result or "error" in result


def test_k8s_history():
    entry = {"host": "k8s-1", "script": "restart_deployment", "result": True}
    k8s_repair.record_history(entry)
    history = k8s_repair.get_k8s_repair_history(limit=1)
    assert history[0] == entry


# -----------------------------------------------------------------------------
# core.alert_service
# -----------------------------------------------------------------------------
@pytest.fixture
def alert_svc(monkeypatch):
    fresh_history = deque(maxlen=100)
    fresh_cache = qo.QueryCache()
    monkeypatch.setattr(alert_service_mod, "alert_history", fresh_history)
    monkeypatch.setattr(alert_service_mod, "query_cache", fresh_cache)
    db_repo = AsyncMock()
    db_repo.update_status = AsyncMock(return_value=True)
    db_repo.create = AsyncMock(return_value="aid")
    monkeypatch.setattr(alert_service_mod, "db_alert_repository", db_repo)
    monkeypatch.setattr(alert_service_mod, "db_clear_alerts", lambda: 0)
    svc = alert_service_mod.AlertService()
    return svc, fresh_history, db_repo


def test_alert_service_get_and_clear(alert_svc):
    svc, history, _ = alert_svc
    history.appendleft(
        {"id": "A1", "severity": "critical", "message": "m", "source": "s", "tenant_id": "t1"}
    )
    history.appendleft(
        {"id": "A2", "severity": "warning", "message": "m", "source": "s", "tenant_id": None}
    )
    history.appendleft(
        {"id": "A3", "severity": "info", "message": "m", "source": "s", "tenant_id": "t1"}
    )

    all_alerts = svc.get_alerts(limit=10)
    assert all_alerts["total"] == 3
    assert len(all_alerts["alerts"]) == 3

    t1 = svc.get_alerts(limit=10, tenant_id="t1")
    assert t1["total"] == 3  # t1 tenant + None tenant included

    cached = svc.get_alerts(limit=10)
    assert cached is all_alerts

    cleared = svc.clear_alerts("1.2.3.4")
    assert cleared["status"] == "ok"
    assert cleared["deleted_count"] == 3
    assert len(history) == 0


def test_alert_service_clear_db_error(alert_svc, monkeypatch):
    svc, history, _ = alert_svc
    history.appendleft({"id": "A1", "severity": "critical", "message": "m", "source": "s"})
    monkeypatch.setattr(
        alert_service_mod, "db_clear_alerts", lambda: (_ for _ in ()).throw(RuntimeError("db down"))
    )
    result = svc.clear_alerts("1.2.3.4")
    assert result["status"] == "ok"
    assert result["deleted_count"] == 1


@pytest.mark.asyncio
async def test_alert_service_update_and_create(alert_svc):
    svc, history, repo = alert_svc
    history.appendleft({"id": "A1", "status": "active"})

    ok = await svc.update_alert_status("A1", "acknowledged")
    assert ok is True
    assert history[0]["status"] == "acknowledged"
    assert "acknowledged_at" in history[0]

    ok2 = await svc.update_alert_status("A1", "resolved")
    assert ok2 is True
    assert "resolved_at" in history[0]

    repo.update_status = AsyncMock(side_effect=RuntimeError("db"))
    ok3 = await svc.update_alert_status("A1", "closed")
    assert ok3 is True

    alert = await svc.create_alert("critical", "disk full", "prometheus")
    assert alert["severity"] == "critical"
    assert alert["status"] == "active"
    assert history[0]["id"] == alert["id"]

    ack = await svc.acknowledge_alert(alert["id"])
    assert ack is True


# -----------------------------------------------------------------------------
# core.alert_providers.prometheus
# -----------------------------------------------------------------------------
def test_prometheus_normalize_variants():
    provider = prom.PrometheusAlertProvider()

    # list input
    out = provider.normalize([{"labels": {"alertname": "HighCPU"}}])
    assert len(out) == 1
    assert out[0]["source"] == "prometheus"

    # empty / invalid input
    assert provider.normalize("bad") == []
    assert len(provider.normalize({})) == 1  # empty dict becomes one empty alert

    # dict group
    group = {
        "alerts": [
            {
                "labels": {
                    "alertname": "MemHigh",
                    "severity": "critical",
                    "value": "92.5",
                    "__name__": "memory_usage",
                    "instance": "srv-1",
                    "job": "node",
                    "platform": "Linux",
                },
                "annotations": {
                    "summary": "Memory high",
                    "description": "Memory usage is high",
                },
                "status": "firing",
                "fingerprint": "fp-123",
                "startsAt": "2026-01-01T00:00:00Z",
            },
            "not-a-dict",
        ]
    }
    normalized = provider.normalize(group)
    assert len(normalized) == 1
    alert = normalized[0]
    assert alert["title"] == "Memory high"
    assert alert["severity"] == "critical"
    assert alert["status"] == "firing"
    assert alert["metric"] == "memory_usage"
    assert alert["value"] == 92.5
    assert alert["platform"] == "linux"
    assert alert["fingerprint"] == "fp-123"

    # resolved single alert
    single = {
        "labels": {"alertname": "DiskFull", "severity": "warning"},
        "annotations": {},
        "status": "resolved",
        "startsAt": "2026-01-02T00:00:00Z",
    }
    out = provider.normalize(single)
    assert len(out) == 1
    assert out[0]["status"] == "resolved"

    # non-dict labels/annotations
    out = provider.normalize({"labels": "invalid", "annotations": [1, 2]})
    assert len(out) == 1


def test_prometheus_safe_float():
    assert prom._safe_float("3.14") == 3.14
    assert prom._safe_float(None) == 0.0
    assert prom._safe_float("abc") == 0.0
    assert prom._safe_float("", default=1.0) == 1.0


def test_prometheus_registry():
    assert get_alert_provider("prometheus") is not None
    assert "prometheus" in get_alert_provider("prometheus").__class__.name


# -----------------------------------------------------------------------------
# additional coverage for core.k8s_repair
# -----------------------------------------------------------------------------
def test_k8s_sanitize_type_error():
    with pytest.raises(ValueError, match="must be a string or number"):
        k8s_repair._sanitize_param(["list"])


@pytest.mark.asyncio
async def test_k8s_inspect_pod_state_success(k8s_mocks):
    result = k8s_repair._inspect_pod_state("default", "web-0")
    assert result["owner_kind"] == "Deployment"
    assert result["has_pvc"] is False


@pytest.mark.asyncio
async def test_k8s_delete_pod_allowed(k8s_mocks, monkeypatch):
    monkeypatch.setattr(
        k8s_repair,
        "_inspect_pod_state",
        lambda namespace, pod: {"owner_kind": "Deployment", "has_pvc": False},
    )
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "delete_pod", {"namespace": "default", "pod": "web-0"}
    )
    assert result.get("blocked", False) is False
    assert result["result"] is True


@pytest.mark.asyncio
async def test_k8s_delete_pod_inspection_error(k8s_mocks, monkeypatch):
    monkeypatch.setattr(
        k8s_repair,
        "_inspect_pod_state",
        lambda namespace, pod: {"error": "kubectl not found"},
    )
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "delete_pod", {"namespace": "default", "pod": "web-0"}
    )
    assert result.get("blocked", False) is False
    assert result["result"] is True


@pytest.mark.asyncio
async def test_k8s_audit_exception(k8s_mocks, monkeypatch):
    monkeypatch.setattr(k8s_repair, "record_audit", MagicMock(side_effect=RuntimeError("audit")))
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert result["result"] is True


@pytest.mark.asyncio
async def test_k8s_record_repair_exception(k8s_mocks, monkeypatch):
    monkeypatch.setattr(k8s_repair, "record_repair", AsyncMock(side_effect=RuntimeError("stats")))
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert result["result"] is True


@pytest.mark.asyncio
async def test_k8s_push_loki_exception(k8s_mocks, monkeypatch):
    monkeypatch.setattr(k8s_repair, "push_to_loki", MagicMock(side_effect=RuntimeError("loki")))
    result = await k8s_repair.execute_repair(
        {"host": "k8s-1"}, "restart_deployment", {"namespace": "default", "deployment": "api"}
    )
    assert result["result"] is True


# -----------------------------------------------------------------------------
# additional coverage for core.ai.llm_router.enhanced_router
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_router_cost_optimized_fallbacks():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="cost_optimized")
    # force select_cheapest_model to None, load balancer will still pick one
    router.cost_optimizer.select_cheapest_model = lambda *a, **k: None
    decision = await router._cost_optimized_routing("prompt", TaskType.GENERAL)
    assert decision.reason == "Fallback to load balancer"

    # open all circuits so load balancer returns None and we hit last resort
    for _ in range(5):
        router.record_failure("gpt-4o-mini", "timeout")
        router.record_failure("gpt-3.5-turbo", "timeout")
    decision = await router._cost_optimized_routing("prompt", TaskType.GENERAL)
    assert decision.reason == "Last resort fallback"


@pytest.mark.asyncio
async def test_router_capability_first_fallback():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="capability_first")
    router.capability_evaluator.get_best_model_for_task = lambda *a, **k: None
    decision = await router._capability_first_routing("prompt", TaskType.GENERAL)
    assert decision.reason == "Fallback to load balancer"

    for _ in range(5):
        router.record_failure("gpt-4o-mini", "timeout")
        router.record_failure("gpt-3.5-turbo", "timeout")
    decision = await router._capability_first_routing("prompt", TaskType.GENERAL)
    assert decision.reason == "Last resort fallback"


@pytest.mark.asyncio
async def test_router_balanced_fallback():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS, strategy="balanced")
    # open top model circuit, second should still be selected if available
    for _ in range(5):
        router.record_failure("gpt-4o-mini", "timeout")
    decision = await router._balanced_routing("prompt", TaskType.GENERAL)
    assert "Balanced" in decision.reason or "Fallback" in decision.reason

    # open all circuits -> fallback
    for _ in range(5):
        router.record_failure("gpt-3.5-turbo", "timeout")
    decision = await router._balanced_routing("prompt", TaskType.GENERAL)
    assert "Fallback" in decision.reason or "Last resort" in decision.reason


@pytest.mark.asyncio
async def test_router_generate_fitting_model(monkeypatch):
    _install_fake_openai(monkeypatch)
    monkeypatch.setenv("AI_API_KEY", "test-key")
    tiny_large = [
        {"model": "tiny", "max_tokens": 2, "context_window": 2, "cost_per_1k": 0.001},
        {"model": "huge", "max_tokens": 128000, "context_window": 128000, "cost_per_1k": 0.1},
    ]
    router = enhanced_router.EnhancedLLMRouter(tiny_large)
    result = await router.generate("this is a test prompt", max_new_tokens=20)
    assert result["content"] == "AI generated analysis result"
    assert result["model"] == "huge"


@pytest.mark.asyncio
async def test_router_generate_api_error(monkeypatch):
    fake_openai = types.ModuleType("openai")

    class _BoomClient:
        def __init__(self, *a, **k):
            self.chat = SimpleNamespace(
                completions=SimpleNamespace(create=AsyncMock(side_effect=RuntimeError("api down")))
            )

    fake_openai.AsyncOpenAI = _BoomClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    monkeypatch.setenv("AI_API_KEY", "test-key")
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS)
    result = await router.generate("prompt")
    assert result["content"].startswith("[AI Router fallback]")


def test_router_find_and_is_available():
    router = enhanced_router.EnhancedLLMRouter(MODEL_CFGS)
    assert router._find_model_config("missing") is None
    assert router._find_model_config("gpt-4o-mini") is not None
    assert router._is_model_available("unknown-model") is True
    assert router._is_model_available("gpt-4o-mini") is True
