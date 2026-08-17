# -*- coding: utf-8 -*-
"""Functional tests for core.rag_engine, core.causal.inference,
core.dr_scenarios, core.exceptions.security and core.hitl.timeout.
"""

import asyncio
import sys
import types
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.db_engine
import core.dr_scenarios as dr_scenarios
import core.rag_engine as rag_engine
from core.causal.graph import CausalEdge, CausalGraph, CausalStrength
from core.causal.inference import RootCauseInference
from core.exceptions.base import ErrorCategory, ErrorSeverity
from core.exceptions.security import (
    AuthenticationException,
    AuthorizationException,
    PermissionDeniedException,
    SecurityException,
)
from core.hitl.approval import ApprovalRequest, ApprovalStatus, ApprovalStep, ApprovalWorkflow
from core.hitl.timeout import ApprovalTimeoutHandler

pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Helpers for core.rag_engine
# ---------------------------------------------------------------------------
class FakeQdrantClient:
    def __init__(self, *args, **kwargs):
        self.location = args[0] if args else kwargs.get("url", kwargs)
        self.created = False
        self.upserted = []
        self.queries = []

    def get_collection(self, name):
        raise RuntimeError(f"collection {name} not found")

    def create_collection(self, **kwargs):
        self.created = True

    def upsert(self, *, collection_name, points):
        self.upserted.append(points)

    def query_points(self, *, collection_name, query, limit, with_payload, score_threshold):
        self.queries.append((query, limit, score_threshold))
        return types.SimpleNamespace(
            points=[
                types.SimpleNamespace(score=0.92, payload={"text": "restart service"}),
                types.SimpleNamespace(score=0.85, payload={"text": "rollback deploy"}),
            ]
        )


class FakeSentenceTransformer:
    def __init__(self, model_name, **kwargs):
        self.name = model_name
        if model_name == "primary-bad":
            raise RuntimeError("primary model failed")

    def get_sentence_embedding_dimension(self):
        return 384


class FakeHttpx:
    def __init__(self, response=None, exc=None):
        self.response = response
        self.exc = exc
        self.calls = []

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if self.exc:
            raise self.exc
        return self.response


class FakeResponse:
    def __init__(self, json_data, raise_status=False):
        self._json = json_data
        self._raise = raise_status
        self.status_code = 200
        self.headers = {}

    def raise_for_status(self):
        if self._raise:
            raise RuntimeError("bad status")

    def json(self):
        return self._json


FAKE_QMODELS = types.SimpleNamespace(
    VectorParams=lambda **kw: kw,
    PointStruct=lambda **kw: kw,
    Distance=types.SimpleNamespace(COSINE="cosine"),
)


def _setup_rag_client(monkeypatch):
    """Wire in a fake Qdrant client instance and fake qmodels."""
    client = FakeQdrantClient()
    monkeypatch.setattr(rag_engine, "_client", client)
    monkeypatch.setattr(rag_engine, "_qmodels", FAKE_QMODELS)
    monkeypatch.setattr(rag_engine, "QdrantClient", FakeQdrantClient)
    monkeypatch.setattr(rag_engine, "QDRANT_URL", "https://qdrant.test")
    return client


def _make_fake_embed(vectors):
    """Return a fake _embed function."""

    def _embed(texts, embed_type="db"):
        return vectors

    return _embed


# ---------------------------------------------------------------------------
# core.rag_engine
# ---------------------------------------------------------------------------
def test_rag_get_client_memory_and_reuse(monkeypatch):
    monkeypatch.setattr(rag_engine, "_client", None)
    monkeypatch.setattr(rag_engine, "_qmodels", FAKE_QMODELS)
    monkeypatch.setattr(rag_engine, "QdrantClient", FakeQdrantClient)
    monkeypatch.setattr(rag_engine, "QDRANT_URL", ":memory:")
    c1 = rag_engine._get_client()
    c2 = rag_engine._get_client()
    assert c1 is c2
    assert c1.location == ":memory:"


def test_rag_get_client_url(monkeypatch):
    monkeypatch.setattr(rag_engine, "_client", None)
    monkeypatch.setattr(rag_engine, "_qmodels", FAKE_QMODELS)
    monkeypatch.setattr(rag_engine, "QdrantClient", FakeQdrantClient)
    monkeypatch.setattr(rag_engine, "QDRANT_URL", "https://qdrant.example:6333")
    client = rag_engine._get_client()
    assert client.location == "https://qdrant.example:6333"


def test_rag_get_client_init_failure(monkeypatch):
    monkeypatch.setattr(rag_engine, "_client", None)
    monkeypatch.setattr(rag_engine, "_qmodels", FAKE_QMODELS)

    class BadQdrant:
        def __init__(self, *a, **k):
            raise RuntimeError("connection refused")

    monkeypatch.setattr(rag_engine, "QdrantClient", BadQdrant)
    monkeypatch.setattr(rag_engine, "QDRANT_URL", "http://bad")
    with pytest.raises(RuntimeError, match="connection refused"):
        rag_engine._get_client()


def test_rag_get_model_primary_fail_fallback_ok(monkeypatch):
    monkeypatch.setattr(rag_engine, "_model", None)
    monkeypatch.setattr(rag_engine, "SentenceTransformer", FakeSentenceTransformer)
    monkeypatch.setattr(rag_engine, "_DEFAULT_EMBEDDING_MODEL", "primary-bad")
    monkeypatch.setattr(rag_engine, "_FALLBACK_EMBEDDING_MODEL", "fallback-ok")
    model = rag_engine._get_model()
    assert model.name == "fallback-ok"


def test_rag_get_model_both_fail(monkeypatch):
    monkeypatch.setattr(rag_engine, "_model", None)

    class AlwaysFail:
        def __init__(self, *a, **k):
            raise RuntimeError("no model")

    monkeypatch.setattr(rag_engine, "SentenceTransformer", AlwaysFail)
    monkeypatch.setattr(rag_engine, "_DEFAULT_EMBEDDING_MODEL", "a")
    monkeypatch.setattr(rag_engine, "_FALLBACK_EMBEDDING_MODEL", "b")
    with pytest.raises(RuntimeError, match="无法加载任何 SentenceTransformer 模型"):
        rag_engine._get_model()


def test_rag_embed_success_with_group_id(monkeypatch):
    monkeypatch.setattr(
        rag_engine,
        "httpx",
        FakeHttpx(
            FakeResponse(
                {
                    "base_resp": {"status_code": 0},
                    "vectors": [[0.1, 0.2, 0.3]],
                }
            )
        ),
    )
    monkeypatch.setattr(
        rag_engine, "AI_CONFIG", {"api_key": "ak", "base_url": "https://api.test/v1"}
    )
    monkeypatch.setenv("MINIMAX_EMBEDDING_MODEL", "embo-01")
    monkeypatch.setenv("MINIMAX_GROUP_ID", "grp-1")
    vectors = rag_engine._embed(["restart service"], embed_type="query")
    assert vectors == [[0.1, 0.2, 0.3]]
    call = rag_engine.httpx.calls[0]
    assert "?GroupId=grp-1" in call[0][0]
    assert call[1]["json"]["type"] == "query"


def test_rag_embed_success_without_group_id(monkeypatch):
    monkeypatch.setattr(
        rag_engine,
        "httpx",
        FakeHttpx(
            FakeResponse(
                {
                    "base_resp": {"status_code": 0},
                    "vectors": [[0.4, 0.5]],
                }
            )
        ),
    )
    monkeypatch.setattr(
        rag_engine, "AI_CONFIG", {"api_key": "ak", "base_url": "https://api.test/v1/"}
    )
    monkeypatch.setenv("MINIMAX_GROUP_ID", "")
    vectors = rag_engine._embed(["cpu high"], embed_type="db")
    assert vectors == [[0.4, 0.5]]
    assert "?GroupId=" not in rag_engine.httpx.calls[0][0][0]


def test_rag_embed_missing_api_key(monkeypatch):
    monkeypatch.setattr(rag_engine, "AI_CONFIG", {"api_key": None})
    monkeypatch.setenv("AI_API_KEY", "")
    with pytest.raises(RuntimeError, match="AI_API_KEY not configured"):
        rag_engine._embed(["x"])


def test_rag_embed_api_returns_error_status(monkeypatch):
    monkeypatch.setattr(
        rag_engine,
        "httpx",
        FakeHttpx(
            FakeResponse(
                {
                    "base_resp": {"status_code": -1, "status_msg": "denied"},
                    "vectors": [[0.1]],
                }
            )
        ),
    )
    monkeypatch.setattr(rag_engine, "AI_CONFIG", {"api_key": "ak"})
    with pytest.raises(RuntimeError, match="MiniMax embedding error"):
        rag_engine._embed(["x"])


def test_rag_embed_empty_vectors(monkeypatch):
    monkeypatch.setattr(
        rag_engine,
        "httpx",
        FakeHttpx(
            FakeResponse(
                {
                    "base_resp": {"status_code": 0},
                    "vectors": None,
                }
            )
        ),
    )
    monkeypatch.setattr(rag_engine, "AI_CONFIG", {"api_key": "ak"})
    with pytest.raises(RuntimeError, match="No embedding vectors returned"):
        rag_engine._embed(["x"])


def test_rag_embed_http_exception(monkeypatch):
    monkeypatch.setattr(rag_engine, "httpx", FakeHttpx(exc=RuntimeError("network down")))
    monkeypatch.setattr(rag_engine, "AI_CONFIG", {"api_key": "ak"})
    with pytest.raises(RuntimeError, match="network down"):
        rag_engine._embed(["x"])


def test_rag_upsert_verify_record(monkeypatch):
    client = _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.0] * 64]))
    payload = {
        "repair_id": 42,
        "alert_id": "cpu_high",
        "script_key": "restart_service",
        "host": "host-01",
        "verified": True,
        "comment": "服务成功重启",
        "evidence": {"logs": ["log-1"]},
        "ignored": None,
    }
    rag_engine.upsert_verify_record(123, payload)
    assert client.created
    assert len(client.upserted) == 1
    points = client.upserted[0]
    assert points[0]["id"] == 123
    assert points[0]["payload"] == payload


def test_rag_upsert_verify_record_empty_vector(monkeypatch):
    _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[]]))
    # Should not raise, but log and return
    rag_engine.upsert_verify_record(124, {"alert_id": "x"})


def test_rag_upsert_record(monkeypatch):
    client = _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.5] * 32]))
    rag_engine.upsert_record(2, "rollback database", payload={"action": "rollback"})
    assert client.created
    assert client.upserted[0][0]["payload"] == {"action": "rollback"}


def test_rag_upsert_records(monkeypatch):
    client = _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.1] * 16, [0.2] * 16]))
    records = [
        {"id": 10, "text": "cpu fix", "payload": {"a": 1}},
        {"text": "disk fix", "payload": {"b": 2}},
    ]
    rag_engine.upsert_records(records)
    assert client.created
    points = client.upserted[0]
    assert len(points) == 2
    assert points[0]["id"] == 10
    assert points[1]["payload"] == {"b": 2}


def test_rag_upsert_records_empty(monkeypatch):
    rag_engine.upsert_records([])  # no-op, no exception


def test_rag_search_similar(monkeypatch):
    _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_RETRIEVAL_SCORE_THRESHOLD", 0.5)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.0] * 64]))
    results = rag_engine.search_similar("restart service", top_k=3)
    assert len(results) == 2
    assert results[0]["score"] == 0.92


def test_rag_search_similar_custom_threshold(monkeypatch):
    client = _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.0] * 64]))
    rag_engine.search_similar("rollback", top_k=5, score_threshold=0.7)
    assert client.queries[0][2] == 0.7


def test_rag_search_similar_empty_vector(monkeypatch):
    _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[]]))
    results = rag_engine.search_similar("x")
    assert results == []


def test_rag_search_similar_uses_default_threshold(monkeypatch):
    client = _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_RETRIEVAL_SCORE_THRESHOLD", 0.65)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.0] * 64]))
    rag_engine.search_similar("x", score_threshold=0.0)
    assert client.queries[0][2] == 0.65


def test_rag_aiops_rag_search_wrapper(monkeypatch):
    _setup_rag_client(monkeypatch)
    monkeypatch.setattr(rag_engine, "_RETRIEVAL_SCORE_THRESHOLD", 0.5)
    monkeypatch.setattr(rag_engine, "_embed", _make_fake_embed([[0.0] * 64]))
    rag = rag_engine.AIOpsRAG()
    results = rag.search_similar("restart")
    assert len(results) == 2


# ---------------------------------------------------------------------------
# core.causal.inference
# ---------------------------------------------------------------------------
def _build_sample_graph():
    g = CausalGraph("infrastructure")
    # chain: db_slow -> cpu_high -> api_latency
    # also db_slow -> api_latency direct
    g.add_edge(CausalEdge("db_slow", "cpu_high", strength=CausalStrength.STRONG, confidence=0.9))
    g.add_edge(
        CausalEdge("cpu_high", "api_latency", strength=CausalStrength.MODERATE, confidence=0.8)
    )
    g.add_edge(CausalEdge("db_slow", "api_latency", strength=CausalStrength.WEAK, confidence=0.6))
    # isolated
    g.add_node("network_blip")
    return g


def test_causal_infer_root_causes_with_ancestors():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    # Only cpu_high is anomalous; its only ancestor is db_slow with STRONG edge
    hypotheses = engine.infer_root_causes({"cpu_high"}, context={"observed_at": "2024-01-01"})
    assert len(hypotheses) == 1
    top = hypotheses[0]
    assert top.node == "db_slow"
    assert top.confidence == 0.9
    assert "strong" in top.explanation
    assert top.evidence["causal_strength"] == "strong"


def test_causal_infer_root_causes_anomalous_ancestor():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    # Both cpu_high and api_latency are anomalous; db_slow causes cpu_high (strong)
    hypotheses = engine.infer_root_causes({"cpu_high", "api_latency"})
    # strongest: db_slow -> cpu_high, not anomalous, strong edge
    assert hypotheses[0].node == "db_slow"
    assert hypotheses[0].confidence == 0.9
    # cpu_high is anomalous, so its influence on api_latency is downscaled
    assert hypotheses[1].node == "cpu_high"
    assert hypotheses[1].confidence == pytest.approx(0.6 * 0.7)


def test_causal_infer_root_causes_no_ancestors():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    hypotheses = engine.infer_root_causes({"network_blip"})
    assert len(hypotheses) == 1
    assert hypotheses[0].node == "network_blip"
    assert hypotheses[0].confidence == 0.5
    assert "No upstream" in hypotheses[0].explanation


def test_causal_infer_unknown_strength():
    g = CausalGraph("x")
    g.add_edge(CausalEdge("a", "b", strength=None, confidence=0.5))  # type: ignore[arg-type]
    engine = RootCauseInference(g)
    h = engine.infer_root_causes({"b"})
    assert h[0].node == "a"
    assert h[0].confidence == 0.5
    assert "unknown" in h[0].explanation


def test_causal_trace_shortest_path():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    path = engine.trace_propagation_path("db_slow", "api_latency")
    # shortest is [db_slow, api_latency]
    assert path == ["db_slow", "api_latency"]


def test_causal_trace_no_path():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    path = engine.trace_propagation_path("api_latency", "db_slow")
    assert path == []


def test_causal_estimate_impact():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    scores = engine.estimate_impact(
        "db_slow", {"db_slow", "cpu_high", "api_latency", "network_blip"}
    )
    assert scores["db_slow"] == 1.0
    # db_slow -> cpu_high (strong): base 1/2, multiplier 1.5
    assert scores["cpu_high"] == pytest.approx(1.0 / 2 * 1.5)
    # db_slow -> api_latency (weak) direct: base 1/2, multiplier 0.5
    assert scores["api_latency"] == pytest.approx(1.0 / 2 * 0.5)
    assert scores["network_blip"] == 0.0


def test_causal_estimate_impact_moderate_path():
    g = _build_sample_graph()
    engine = RootCauseInference(g)
    scores = engine.estimate_impact("db_slow", {"api_latency"})
    # shortest: db_slow -> api_latency, strong? Wait we set db_slow->api_latency WEAK
    # so multiplier 0.5, base 0.5 => 0.25
    assert scores["api_latency"] == pytest.approx(0.25)


# ---------------------------------------------------------------------------
# core.dr_scenarios
# ---------------------------------------------------------------------------
class FakeAsyncSession:
    async def execute(self, query):
        return None


class FakeAsyncSessionLocal:
    def __call__(self):
        return self

    async def __aenter__(self):
        return FakeAsyncSession()

    async def __aexit__(self, *args):
        return None


class FakeRedis:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def ping(self):
        return True


class FakeHttpxAsyncClient:
    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return None

    async def get(self, url):
        return types.SimpleNamespace(status_code=200)


@pytest.fixture
def external_deps(monkeypatch):
    """Mock DB, Redis, and HTTP for DR scenario tests."""
    monkeypatch.setattr(core.db_engine, "AsyncSessionLocal", FakeAsyncSessionLocal())
    fake_redis = types.ModuleType("redis")
    fake_redis.Redis = FakeRedis
    monkeypatch.setitem(sys.modules, "redis", fake_redis)
    monkeypatch.setattr("httpx.AsyncClient", FakeHttpxAsyncClient)


def test_dr_check_database(external_deps):
    scenario = dr_scenarios.DRScenario("db", "", [{"type": "check_database"}])
    result = asyncio.run(scenario._execute_step({"type": "check_database"}))
    assert result["status"] == "healthy"


def test_dr_check_redis(external_deps):
    scenario = dr_scenarios.DRScenario("redis", "", [])
    result = asyncio.run(scenario._execute_step({"type": "check_redis"}))
    assert result["status"] == "healthy"


def test_dr_check_api(external_deps):
    scenario = dr_scenarios.DRScenario("api", "", [])
    result = asyncio.run(scenario._execute_step({"type": "check_api", "endpoint": "/health"}))
    assert result["status"] == "healthy"
    assert result["status_code"] == 200


def test_dr_simulate_failure():
    scenario = dr_scenarios.DRScenario("fail", "", [])
    result = asyncio.run(
        scenario._execute_step(
            {
                "type": "simulate_failure",
                "description": "simulate",
                "failure_type": "disk_full",
            }
        )
    )
    assert result["status"] == "simulated"
    assert result["failure_type"] == "disk_full"


def test_dr_simulate_failure_missing_type():
    scenario = dr_scenarios.DRScenario("fail", "", [])
    result = asyncio.run(scenario._execute_step({"type": "simulate_failure"}))
    assert result["status"] == "error"
    assert "failure_type is required" in result["error"]


def test_dr_restore_backup():
    scenario = dr_scenarios.DRScenario("restore", "", [])
    result = asyncio.run(scenario._execute_step({"type": "restore_backup"}))
    assert result["status"] == "restored"


def test_dr_unknown_step():
    scenario = dr_scenarios.DRScenario("unknown", "", [])
    result = asyncio.run(scenario._execute_step({"type": "weird"}))
    assert result is None


def test_dr_scenario_execute_success(external_deps):
    scenario = dr_scenarios.DRScenario(
        "dr-test",
        "test scenario",
        steps=[
            {"type": "check_database", "description": "db"},
            {"type": "check_redis", "description": "redis"},
            {"type": "check_api", "description": "api", "endpoint": "/api/v1/health"},
            {"type": "simulate_failure", "description": "fail", "failure_type": "db_down"},
            {"type": "restore_backup", "description": "restore"},
        ],
    )
    report = asyncio.run(scenario.execute())
    assert report["status"] == "completed"
    assert len(report["results"]) == 5
    assert report["results"][0]["status"] == "success"


def test_dr_scenario_execute_failure():
    scenario = dr_scenarios.DRScenario(
        "dr-fail", "fail", [{"type": "check_database", "description": "db check"}]
    )
    scenario._check_database = AsyncMock(side_effect=RuntimeError("DB down"))
    report = asyncio.run(scenario.execute())
    assert report["status"] == "failed"
    assert report["results"][0]["status"] == "failed"
    assert "DB down" in report["results"][0]["error"]


def test_run_dr_scenario_found(external_deps):
    result = asyncio.run(dr_scenarios.run_dr_scenario("redis_cache_failure"))
    assert result["scenario"] == "Redis Cache Failure"


def test_run_dr_scenario_not_found():
    result = asyncio.run(dr_scenarios.run_dr_scenario("does_not_exist"))
    assert result["status"] == "error"
    assert "not found" in result["message"]


def test_list_dr_scenarios():
    scenarios = asyncio.run(dr_scenarios.list_dr_scenarios())
    assert any(s["name"] == "database_failover" for s in scenarios)
    assert all("steps_count" in s for s in scenarios)


# ---------------------------------------------------------------------------
# core.exceptions.security
# ---------------------------------------------------------------------------
def test_security_exception_default():
    ex = SecurityException("token missing")
    assert ex.message == "token missing"
    assert ex.error_code == "02_01_0001"
    assert ex.category == ErrorCategory.SECURITY
    assert ex.severity == ErrorSeverity.WARNING
    assert ex.context == {}
    assert ex.to_dict()["error_type"] == "SecurityException"


def test_security_exception_with_context_and_original():
    original = ValueError("bad")
    ex = SecurityException("x", context={"ip": "1.1.1.1"}, original_exception=original)
    assert ex.context["ip"] == "1.1.1.1"
    assert ex.original_exception is original
    assert ex.stack_trace is not None
    ex.with_context(user="admin")
    assert ex.context["user"] == "admin"


def test_authentication_exception_token_masking():
    long_token = "0123456789abcdef"  # > 12 chars
    ex = AuthenticationException("auth failed", token=long_token, expired_at="2024-01-01")
    assert ex.context["token"] == "01234567...cdef"
    assert ex.context["expired_at"] == "2024-01-01"
    assert ex.token == long_token


def test_authentication_exception_short_token():
    ex = AuthenticationException("auth failed", token="12345")
    assert ex.context["token"] == "***"


def test_authorization_exception():
    ex = AuthorizationException(
        "no permission",
        required_role="admin",
        current_role="viewer",
        context={"path": "/sensitive"},
    )
    assert ex.error_code == "02_03_0001"
    assert ex.severity == ErrorSeverity.ERROR
    assert ex.context["required_role"] == "admin"
    assert ex.context["current_role"] == "viewer"


def test_authorization_exception_without_roles():
    ex = AuthorizationException("no permission")
    assert "required_role" not in ex.context


def test_permission_denied_exception():
    ex = PermissionDeniedException(
        "denied",
        resource="/api/runbooks",
        action="DELETE",
    )
    assert ex.error_code == "02_03_0002"
    assert ex.context["resource"] == "/api/runbooks"
    assert ex.context["action"] == "DELETE"


def test_permission_denied_exception_without_resource():
    ex = PermissionDeniedException("denied")
    assert "resource" not in ex.context


# ---------------------------------------------------------------------------
# core.hitl.timeout
# ---------------------------------------------------------------------------
def _build_timeout_workflow():
    workflow = ApprovalWorkflow()
    steps = [
        ApprovalStep(step_id="s1", name="level-1", approver="alice", timeout_minutes=60),
        ApprovalStep(step_id="s2", name="level-2", approver="bob", timeout_minutes=60),
    ]
    request = workflow.create_request(
        workflow_id="wf-1",
        title="rollback",
        description="rollback db",
        steps=steps,
    )
    return workflow, request


def test_timeout_handle_escalate(monkeypatch):
    monkeypatch.setattr("core.hitl.timeout.asyncio.sleep", AsyncMock())
    workflow, request = _build_timeout_workflow()
    step0 = request.steps[0]
    step1 = request.steps[1]
    notifier = AsyncMock()
    handler = ApprovalTimeoutHandler(workflow, notifier)

    async def _run():
        await handler._handle_timeout(request, step0)
        # await the re-armed monitoring task
        task = handler.timeout_tasks.get(request.request_id)
        if task:
            await task

    asyncio.run(_run())
    assert step0.status == ApprovalStatus.TIMEOUT
    assert request.current_step == 1
    assert step1.status == ApprovalStatus.TIMEOUT
    assert request.status == ApprovalStatus.REJECTED
    assert request.request_id in workflow.completed_requests
    assert request.request_id not in workflow.active_requests
    assert notifier.send_approval_request.awaited
    assert notifier.send_approval_request.call_args[0][0] == "bob"


def test_timeout_handle_reject(monkeypatch):
    monkeypatch.setattr("core.hitl.timeout.asyncio.sleep", AsyncMock())
    workflow = ApprovalWorkflow()
    step = ApprovalStep(step_id="s1", name="level-1", approver="alice", timeout_minutes=60)
    request = workflow.create_request(
        workflow_id="wf-2",
        title="restart",
        description="restart svc",
        steps=[step],
    )
    handler = ApprovalTimeoutHandler(workflow)
    asyncio.run(handler._handle_timeout(request, step))
    assert step.status == ApprovalStatus.TIMEOUT
    assert request.status == ApprovalStatus.REJECTED
    assert request.request_id in workflow.completed_requests
    assert request.request_id not in workflow.active_requests


def test_timeout_find_next_pending_step():
    workflow, request = _build_timeout_workflow()
    handler = ApprovalTimeoutHandler(workflow)
    step0 = request.steps[0]
    step1 = request.steps[1]
    step0.status = ApprovalStatus.TIMEOUT
    step1.status = ApprovalStatus.PENDING
    assert handler._find_next_pending_step(request, step0) == 1

    step1.status = ApprovalStatus.TIMEOUT
    assert handler._find_next_pending_step(request, step0) is None

    fake_step = ApprovalStep(step_id="missing", name="x", approver="none")
    assert handler._find_next_pending_step(request, fake_step) is None


def test_timeout_notify_step():
    workflow, request = _build_timeout_workflow()
    notifier = AsyncMock()
    handler = ApprovalTimeoutHandler(workflow, notifier)
    asyncio.run(handler._notify_step(request, request.steps[0]))
    notifier.send_approval_request.assert_awaited_once_with(
        "alice",
        request.to_dict(),
    )


def test_timeout_notify_step_no_notifier():
    workflow, request = _build_timeout_workflow()
    handler = ApprovalTimeoutHandler(workflow)
    # should do nothing and not raise
    asyncio.run(handler._notify_step(request, request.steps[0]))


def test_timeout_notify_step_failure():
    workflow, request = _build_timeout_workflow()
    notifier = AsyncMock(side_effect=RuntimeError("send failed"))
    handler = ApprovalTimeoutHandler(workflow, notifier)
    asyncio.run(handler._notify_step(request, request.steps[0]))


def test_timeout_monitor_missing_request():
    workflow = ApprovalWorkflow()
    handler = ApprovalTimeoutHandler(workflow)
    asyncio.run(handler.monitor_timeout("missing"))


def test_timeout_monitor_current_step_out_of_range():
    workflow = ApprovalWorkflow()
    request = workflow.create_request(
        workflow_id="wf-3",
        title="t",
        description="d",
        steps=[],
    )
    request.current_step = 1
    handler = ApprovalTimeoutHandler(workflow)
    asyncio.run(handler.monitor_timeout(request.request_id))


def test_timeout_monitor_reaches_timeout(monkeypatch):
    monkeypatch.setattr("core.hitl.timeout.asyncio.sleep", AsyncMock())
    workflow = ApprovalWorkflow()
    step = ApprovalStep(step_id="s1", name="level-1", approver="alice", timeout_minutes=0)
    request = workflow.create_request(
        workflow_id="wf-4",
        title="t",
        description="d",
        steps=[step],
    )
    handler = ApprovalTimeoutHandler(workflow)

    async def _run():
        handler.start_monitoring(request.request_id)
        task = handler.timeout_tasks[request.request_id]
        await task

    asyncio.run(_run())
    assert step.status == ApprovalStatus.TIMEOUT
    assert request.request_id in workflow.completed_requests


def test_timeout_start_monitoring_existing_task():
    workflow, request = _build_timeout_workflow()
    handler = ApprovalTimeoutHandler(workflow)
    handler.timeout_tasks[request.request_id] = AsyncMock()
    handler.start_monitoring(request.request_id)  # should return immediately


def test_timeout_start_monitoring_no_event_loop():
    workflow, request = _build_timeout_workflow()
    handler = ApprovalTimeoutHandler(workflow)
    # no event loop in this synchronous test
    handler.start_monitoring(request.request_id)
    assert request.request_id not in handler.timeout_tasks


def test_timeout_stop_monitoring():
    workflow, request = _build_timeout_workflow()
    handler = ApprovalTimeoutHandler(workflow)

    async def _run():
        handler.start_monitoring(request.request_id)
        handler.stop_monitoring(request.request_id)

    asyncio.run(_run())
    assert request.request_id not in handler.timeout_tasks


def test_timeout_stop_monitoring_unknown():
    workflow = ApprovalWorkflow()
    handler = ApprovalTimeoutHandler(workflow)
    # should not raise
    handler.stop_monitoring("unknown")
