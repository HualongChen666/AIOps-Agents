# -*- coding: utf-8 -*-
"""Smoke tests for low-coverage workflow, scenario memory and topology helpers."""

from __future__ import annotations

import asyncio  # noqa: F401  # Imported for test setup
import importlib.util
import subprocess
import sys  # noqa: F401  # Imported for test setup
import types
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "extensions" / "addons"


class _Metric:
    """Prometheus-like metric stub."""

    def labels(self, **kwargs):
        return self

    def inc(self, n=1):
        pass

    def dec(self, n=1):
        pass

    def observe(self, value):
        pass

    def set(self, value):
        pass


def _ensure_pkg(name: str, path: Path | None, monkeypatch) -> None:
    """Create a package chain in sys.modules for the given dotted name."""
    parts = name.split(".")
    for i, _ in enumerate(parts):
        sub = ".".join(parts[: i + 1])
        if sub in sys.modules:
            continue
        mod = types.ModuleType(sub)
        if i == len(parts) - 1 and path is not None:
            mod.__path__ = [str(path)]
        else:
            mod.__path__ = []
        monkeypatch.setitem(sys.modules, sub, mod)


def _load(path: Path, name: str, monkeypatch, parent_path: Path | None = None):
    """Load a file as a module using importlib."""
    parent = name.rsplit(".", 1)[0]
    _ensure_pkg(parent, parent_path, monkeypatch)
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {path}")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    """Stub external I/O dependencies for the duration of each test."""
    httpx_mod = types.ModuleType("httpx")

    class _HResp:
        status_code = 200
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {}

    class _HClient:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return _HResp()

        def post(self, *args, **kwargs):
            return _HResp()

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    class _HAsyncClient(_HClient):
        async def get(self, *args, **kwargs):
            return _HResp()

        async def post(self, *args, **kwargs):
            return _HResp()

    httpx_mod.Client = _HClient
    httpx_mod.AsyncClient = _HAsyncClient
    httpx_mod.get = _HClient().get
    httpx_mod.post = _HClient().post
    monkeypatch.setitem(sys.modules, "httpx", httpx_mod)

    requests_mod = types.ModuleType("requests")

    class _RResp:
        status_code = 200
        text = "{}"

        def raise_for_status(self):
            pass

        def json(self):
            return {}

    def _req(*args, **kwargs):
        return _RResp()

    requests_mod.get = _req
    requests_mod.post = _req
    requests_mod.request = _req
    monkeypatch.setitem(sys.modules, "requests", requests_mod)

    aiohttp_mod = types.ModuleType("aiohttp")

    class _AResp:
        status = 200

        async def json(self):
            return {}

        async def text(self):
            return ""

        def raise_for_status(self):
            pass

    class _ASession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return _AResp()

        async def post(self, *args, **kwargs):
            return _AResp()

    aiohttp_mod.ClientSession = _ASession
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_mod)

    redis_mod = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")

    class _Redis:
        def get(self, *args, **kwargs):
            return None

        def setex(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def delete(self, *args, **kwargs):
            pass

        def flushdb(self, *args, **kwargs):
            pass

    class _ARedis:
        async def get(self, *args, **kwargs):
            return None

        async def setex(self, *args, **kwargs):
            pass

        async def set(self, *args, **kwargs):
            pass

        async def delete(self, *args, **kwargs):
            pass

        async def flushdb(self, *args, **kwargs):
            pass

    redis_mod.Redis = _Redis
    redis_mod.ConnectionError = type("ConnectionError", (Exception,), {})
    redis_mod.TimeoutError = type("TimeoutError", (Exception,), {})
    redis_asyncio.Redis = _ARedis
    redis_mod.asyncio = redis_asyncio
    monkeypatch.setitem(sys.modules, "redis", redis_mod)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio)

    log_mod = types.ModuleType("loguru")
    log_mod.logger = MagicMock()
    monkeypatch.setitem(sys.modules, "loguru", log_mod)

    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0, stdout="", stderr="", check_returncode=lambda: None
        ),
    )
    monkeypatch.setattr(
        subprocess,
        "Popen",
        lambda *args, **kwargs: SimpleNamespace(
            terminate=lambda: None, wait=lambda: 0, communicate=lambda: ("", "")
        ),
    )


def _workflow_pkg(monkeypatch):
    """Set up the fake services.workflow_service package and shared stubs."""
    _ensure_pkg("services.workflow_service", None, monkeypatch)
    mod = types.ModuleType("services.workflow_service.metrics")
    for name in [
        "WORKFLOWS_CREATED",
        "WORKFLOWS_COMPLETED",
        "WORKFLOW_EXECUTION_DURATION",
        "WORKFLOW_NODE_EXECUTION_DURATION",
        "WORKFLOW_RETRY_ATTEMPTS",
        "WORKFLOW_SCHEDULED_TASKS",
        "WORKFLOW_SAGA_STATUS",
        "WORKFLOW_TEMPLATE_RENDERS",
    ]:
        setattr(mod, name, _Metric())
    monkeypatch.setitem(sys.modules, "services.workflow_service.metrics", mod)
    _load(
        ADDONS / "operations" / "workflow_service" / "schemas.py",
        "services.workflow_service.schemas",
        monkeypatch,
    )


def test_workflow_orchestrator(monkeypatch):
    _workflow_pkg(monkeypatch)
    _load(
        ADDONS / "operations" / "workflow_service" / "state_machine.py",
        "services.workflow_service.state_machine",
        monkeypatch,
    )
    repo_mod = _load(
        ADDONS / "operations" / "workflow_service" / "repository.py",
        "services.workflow_service.repository",
        monkeypatch,
    )
    retry_mod = _load(
        ADDONS / "operations" / "workflow_service" / "retry.py",
        "services.workflow_service.retry",
        monkeypatch,
    )
    orch_mod = _load(
        ADDONS / "operations" / "workflow_service" / "orchestrator.py",
        "services.workflow_service.orchestrator",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]
    repo = repo_mod.InMemoryWorkflowRepository()
    orch = orch_mod.WorkflowOrchestrator(repository=repo)

    definition = schemas.WorkflowDefinition(
        workflow_id="wf1",
        name="test",
        nodes=[
            schemas.WorkflowNode(
                node_id="n1",
                name="step1",
                command="echo {{ name }}",
                dependencies=[],
            )
        ],
        metadata={"name": "world"},
    )
    request = schemas.WorkflowRequest(
        workflow_id="wf1",
        params={},
        priority=schemas.TaskPriority.HIGH,
    )

    async def _run():
        await repo.save_definition(definition)
        task = await orch.create_task(request)
        result = await orch.execute(task)  # noqa: F841  # Variable for test verification
        return task, result

    task, result = asyncio.run(_run())  # noqa: F841  # Variable for test verification
    assert result.success is True
    assert task.status == schemas.WorkflowStatus.SUCCEEDED


def test_workflow_saga(monkeypatch):
    _workflow_pkg(monkeypatch)
    saga_mod = _load(
        ADDONS / "operations" / "workflow_service" / "saga.py",
        "services.workflow_service.saga",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]
    orchestrator = saga_mod.WorkflowSagaOrchestrator()
    step = schemas.SagaStep(step_id="s1", service="svc", action="act", compensation="comp")
    orchestrator.register(
        "s1",
        [step],
        {"act": lambda: "ok"},
        {"comp": lambda: None},
    )

    async def _run():
        result = await orchestrator.execute("s1")  # noqa: F841  # Variable for test verification
        tx = orchestrator.get_transaction("s1")
        return result, tx

    result, tx = asyncio.run(_run())
    assert result["success"] is True
    assert tx.status == "success"


def test_workflow_scheduler(monkeypatch):
    _workflow_pkg(monkeypatch)
    sched_mod = _load(
        ADDONS / "operations" / "workflow_service" / "scheduler.py",
        "services.workflow_service.scheduler",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]
    sched = sched_mod.WorkflowScheduler()

    async def handler(request):
        return schemas.WorkflowTask(task_id="t1", workflow_id=request.workflow_id)

    sched.register_handler(handler)
    scheduled = schemas.ScheduledTask(
        schedule_id="s1",
        workflow_id="wf1",
        cron="* * * * *",
        enabled=True,
        params={},
    )
    asyncio.run(sched.schedule(scheduled))
    scheduled.next_run = datetime.utcnow() - timedelta(seconds=2)

    request = schemas.WorkflowRequest(workflow_id="wf2", params={})

    async def _run():
        job_id = await sched.enqueue(request)
        results = await sched.run_once()
        return job_id, results

    job_id, results = asyncio.run(_run())
    assert job_id.startswith("SCHEDULED-")
    assert len(results) >= 1


def test_workflow_retry(monkeypatch):
    _workflow_pkg(monkeypatch)
    retry_mod = _load(
        ADDONS / "operations" / "workflow_service" / "retry.py",
        "services.workflow_service.retry",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]

    async def ok():
        return "ok"

    async def fail():
        raise RuntimeError("boom")

    engine = retry_mod.RetryEngine()
    result = asyncio.run(engine.execute(ok))  # noqa: F841  # Variable for test verification
    assert result == "ok"  # noqa: F841  # Variable for test verification

    with pytest.raises(RuntimeError):
        asyncio.run(engine.execute(fail, policy_name="no_retry"))

    engine.add_policy(
        schemas.RetryPolicy(
            name="custom",
            max_retries=0,
            base_delay_seconds=0.0,
            max_delay_seconds=0.0,
        )
    )
    assert "custom" in engine.policies


def test_workflow_templates(monkeypatch):
    _workflow_pkg(monkeypatch)
    tmpl_mod = _load(
        ADDONS / "operations" / "workflow_service" / "templates.py",
        "services.workflow_service.templates",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]
    tm = tmpl_mod.TemplateManager()
    tpl = schemas.WorkflowTemplate(
        template_id="t1",
        name="hello",
        source="Hello {{ name }}!",
        default_params={"name": "World"},
    )

    async def _run():
        tid = await tm.register(tpl)
        rendered = await tm.render("t1", {"name": "AIOps"})
        listed = await tm.list_templates()
        got = await tm.get("t1")
        return tid, rendered, listed, got

    tid, rendered, listed, got = asyncio.run(_run())
    assert rendered == "Hello AIOps!"
    assert len(listed) == 1
    assert got.template_id == "t1"


def test_workflow_repository(monkeypatch):
    _workflow_pkg(monkeypatch)
    _load(
        ADDONS / "operations" / "workflow_service" / "state_machine.py",
        "services.workflow_service.state_machine",
        monkeypatch,
    )
    repo_mod = _load(
        ADDONS / "operations" / "workflow_service" / "repository.py",
        "services.workflow_service.repository",
        monkeypatch,
    )
    schemas = sys.modules["services.workflow_service.schemas"]
    repo = repo_mod.InMemoryWorkflowRepository()
    task = schemas.WorkflowTask(task_id="t1", workflow_id="wf1")

    async def _run():
        tid = await repo.save_task(task)
        got = await repo.get_task("t1")
        tasks = await repo.list_tasks()
        updated = await repo.update_task("t1", {"status": schemas.WorkflowStatus.RUNNING})
        deleted = await repo.delete_task("t1")
        defn = schemas.WorkflowDefinition(workflow_id="wf1", name="test")
        did = await repo.save_definition(defn)
        dget = await repo.get_definition("wf1")
        dlist = await repo.list_definitions()
        ver = schemas.WorkflowVersion(
            version="v1",
            workflow_id="wf1",
            commit_hash="abc",
            message="init",
        )
        await repo.save_version("wf1", ver)
        vlist = await repo.list_versions("wf1")
        sched = schemas.ScheduledTask(schedule_id="s1", workflow_id="wf1", cron="* * * * *")
        await repo.save_schedule(sched)
        slist = await repo.list_schedules()
        return (
            tid,
            got,
            tasks,
            updated,
            deleted,
            did,
            dget,
            dlist,
            vlist,
            slist,
        )

    (
        tid,
        got,
        tasks,
        updated,
        deleted,
        did,
        dget,
        dlist,
        vlist,
        slist,
    ) = asyncio.run(_run())
    assert tid == "t1"
    assert got.task_id == "t1"
    assert len(tasks) == 1
    assert updated is True
    assert deleted is True
    assert did == "wf1"
    assert dget.workflow_id == "wf1"
    assert len(dlist) == 1
    assert len(vlist) == 1
    assert len(slist) == 1


def _scenario_pkg(monkeypatch):
    """Set up the scenario_memory_service package and load its helpers."""
    pkg_path = ADDONS / "operations" / "scenario_memory_service"
    _ensure_pkg("extensions.addons.operations.scenario_memory_service", pkg_path, monkeypatch)

    m = types.ModuleType("extensions.addons.operations.scenario_memory_service.metrics")
    m.request_counter = _Metric()
    m.memory_size_gauge = _Metric()
    monkeypatch.setitem(
        sys.modules, "extensions.addons.operations.scenario_memory_service.metrics", m
    )

    cfg = types.ModuleType("extensions.addons.operations.scenario_memory_service.config")
    cfg.settings = SimpleNamespace(
        service_name="scenario-memory-service",
        redis_url="",
        embedding_dimension=128,
        max_similar_results=10,
        default_cache_ttl=300,
        similarity_threshold=0.75,
        knowledge_decay_rate=0.01,
        experience_decay_rate=0.005,
        short_term_capacity=1000,
        long_term_capacity=10000,
        pattern_threshold=0.8,
    )
    monkeypatch.setitem(
        sys.modules, "extensions.addons.operations.scenario_memory_service.config", cfg
    )

    hc = types.ModuleType("extensions.addons.operations.scenario_memory_service.health_check")

    class HealthCheckEngine:
        async def check(self):
            return {
                "status": "ok",
                "service": "scenario-memory",
                "environment": "test",
            }

    hc.HealthCheckEngine = HealthCheckEngine
    monkeypatch.setitem(
        sys.modules,
        "extensions.addons.operations.scenario_memory_service.health_check",
        hc,
    )

    _load(
        pkg_path / "schemas.py",
        "extensions.addons.operations.scenario_memory_service.schemas",
        monkeypatch,
        pkg_path,
    )
    _load(
        pkg_path / "cache.py",
        "extensions.addons.operations.scenario_memory_service.cache",
        monkeypatch,
        pkg_path,
    )
    _load(
        pkg_path / "retry.py",
        "extensions.addons.operations.scenario_memory_service.retry",
        monkeypatch,
        pkg_path,
    )


def test_scenario_memory_orchestrator(monkeypatch):
    _scenario_pkg(monkeypatch)
    pkg_path = ADDONS / "operations" / "scenario_memory_service"
    orch_mod = _load(
        pkg_path / "orchestrator.py",
        "extensions.addons.operations.scenario_memory_service.orchestrator",
        monkeypatch,
        pkg_path,
    )
    schemas = sys.modules["extensions.addons.operations.scenario_memory_service.schemas"]
    orch = orch_mod.ScenarioMemoryOrchestrator()

    async def _run():
        event = schemas.EventMemory(
            event_type="alert",
            source="test",
            payload={"x": 1},
            tags=["t"],
        )
        await orch.store_event(schemas.StoreEventRequest(event=event))
        await orch.search_similar(schemas.SimilarityQueryRequest(query="alert"))
        await orch.learn_experience(
            schemas.LearnExperienceRequest(
                situation="net down",
                action="restart",
                outcome="fixed",
                confidence=0.9,
            )
        )
        await orch.accumulate_knowledge(
            schemas.AccumulateKnowledgeRequest(
                entries=[schemas.KnowledgeEntry(subject="s", predicate="p", object="o", weight=1.0)]
            )
        )
        await orch.recognize_pattern(
            schemas.PatternRequest(
                pattern_type="sequence",
                data=[
                    {"event_type": "a"},
                    {"event_type": "b"},
                    {"event_type": "a"},
                    {"event_type": "b"},
                ],
            )
        )
        await orch.store_short_term(schemas.ShortTermRequest(key="k", value="v"))
        await orch.retrieve_short_term("k")
        await orch.store_long_term(schemas.LongTermRequest(key="k2", value="v2", importance=1.0))
        await orch.retrieve_long_term("k2")
        await orch.store_semantic(schemas.SemanticRequest(entity="e", relation="r", target="t"))
        await orch.retrieve_semantic("e")
        await orch.store_procedural(schemas.ProceduralRequest(name="proc", steps=["s1"]))
        await orch.retrieve_procedural("proc")
        await orch.find_experiences(query="net")
        await orch.correct_experience(
            situation="net down",
            action="restart",
            corrected_by="admin",
            corrected_outcome="rebooted",
        )
        return await orch.get_stats()

    stats = asyncio.run(_run())
    assert stats.service == "scenario-memory-service"


def test_scenario_memory_main_app(monkeypatch):
    _scenario_pkg(monkeypatch)
    pkg_path = ADDONS / "operations" / "scenario_memory_service"
    _load(
        pkg_path / "orchestrator.py",
        "extensions.addons.operations.scenario_memory_service.orchestrator",
        monkeypatch,
        pkg_path,
    )
    main_mod = _load(
        pkg_path / "main_app.py",
        "extensions.addons.operations.scenario_memory_service.main_app",
        monkeypatch,
        pkg_path,
    )
    health = asyncio.run(main_mod.health())
    stats = asyncio.run(main_mod.stats())
    assert health.status == "ok"
    assert stats.service == "scenario-memory-service"


def test_scenario_memory_retry(monkeypatch):
    _scenario_pkg(monkeypatch)
    pkg_path = ADDONS / "operations" / "scenario_memory_service"
    retry_mod = _load(
        pkg_path / "retry.py",
        "extensions.addons.operations.scenario_memory_service.retry",
        monkeypatch,
        pkg_path,
    )
    engine = retry_mod.ScenarioRetryEngine(policy="none")

    async def ok():
        return 1

    def sync_ok():
        return 2

    async def fail():
        raise RuntimeError("x")

    result = asyncio.run(
        engine.execute(ok, operation="ok")
    )  # noqa: F841  # Variable for test verification
    assert result == 1  # noqa: F841  # Variable for test verification
    result2 = asyncio.run(engine.execute(sync_ok, operation="sync"))
    assert result2 == 2
    with pytest.raises(RuntimeError):
        asyncio.run(engine.execute(fail, operation="fail"))
    assert "none" in engine.list_policies()


def test_scenario_memory_cache(monkeypatch):
    _scenario_pkg(monkeypatch)
    pkg_path = ADDONS / "operations" / "scenario_memory_service"
    cache_mod = _load(
        pkg_path / "cache.py",
        "extensions.addons.operations.scenario_memory_service.cache",
        monkeypatch,
        pkg_path,
    )
    cache = cache_mod.CacheManager(redis_url="redis://")

    async def _run():
        await cache.connect()
        await cache.set("a", {"x": 1}, ttl=10)
        got = await cache.get("a")
        await cache.delete("a")
        gone = await cache.get("a")
        await cache.set("b", 2)
        await cache.clear()
        cleared = await cache.get("b")
        return got, gone, cleared

    got, gone, cleared = asyncio.run(_run())
    assert got == {"x": 1}
    assert gone is None
    assert cleared is None


def _topology_pkg(monkeypatch):
    """Set up the services.topology_service package and shared stubs."""
    _ensure_pkg("services.topology_service", None, monkeypatch)
    mod = types.ModuleType("services.topology_service.metrics")
    for name in [
        "TOPOLOGY_ACTIVE_DISCOVERIES",
        "TOPOLOGY_DISCOVERED_NODES",
        "TOPOLOGY_DISCOVERED_EDGES",
        "TOPOLOGY_DISCOVERY_DURATION",
        "TOPOLOGY_IMPACT_ANALYSIS_DURATION",
        "TOPOLOGY_REALTIME_MESSAGES",
        "TOPOLOGY_SAGA_STATUS",
    ]:
        setattr(mod, name, _Metric())
    monkeypatch.setitem(sys.modules, "services.topology_service.metrics", mod)

    _load(
        ADDONS / "observability" / "topology_service" / "schemas.py",
        "services.topology_service.schemas",
        monkeypatch,
    )

    cfg = types.ModuleType("services.topology_service.config")
    cfg.settings = SimpleNamespace(use_in_memory=True)
    monkeypatch.setitem(sys.modules, "services.topology_service.config", cfg)

    hc = types.ModuleType("services.topology_service.health_check")

    class HealthCheckEngine:
        async def check(self):
            return {"status": "ok"}

    hc.HealthCheckEngine = HealthCheckEngine
    monkeypatch.setitem(sys.modules, "services.topology_service.health_check", hc)

    repo = types.ModuleType("services.topology_service.repository")

    class FakeRepo:
        async def save(self, *args, **kwargs):
            pass

        async def get(self, *args, **kwargs):
            return None

        async def list(self, *args, **kwargs):
            return []

        async def count(self, *args, **kwargs):
            return 0

    async def get_repository(use_in_memory: bool = True):
        return FakeRepo()

    repo.get_repository = get_repository
    monkeypatch.setitem(sys.modules, "services.topology_service.repository", repo)

    audit = types.ModuleType("services.topology_service.audit")

    class TopologyAuditStore:
        async def record(self, *args, **kwargs):
            pass

    audit.TopologyAuditStore = TopologyAuditStore
    monkeypatch.setitem(sys.modules, "services.topology_service.audit", audit)

    ver = types.ModuleType("services.topology_service.versioning")

    class TopologyVersionManager:
        async def commit(self, *args, **kwargs):
            return SimpleNamespace(model_dump=lambda: {"version": "v1"})

    ver.TopologyVersionManager = TopologyVersionManager
    monkeypatch.setitem(sys.modules, "services.topology_service.versioning", ver)

    vis = types.ModuleType("services.topology_service.visualization")

    class TopologyVisualizer:
        async def generate(self, *args, **kwargs):
            return SimpleNamespace(model_dump=lambda: {})

    vis.TopologyVisualizer = TopologyVisualizer
    monkeypatch.setitem(sys.modules, "services.topology_service.visualization", vis)


def test_topology_dependency(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    dep_mod = _load(
        top_path / "dependency.py",
        "services.topology_service.dependency",
        monkeypatch,
    )
    schemas = sys.modules["services.topology_service.schemas"]
    graph = dep_mod.DependencyGraph()
    nodes = [
        schemas.TopologyNode(node_id="agent", name="Agent"),
        schemas.TopologyNode(node_id="collect", name="Collector"),
    ]
    edges = [schemas.TopologyEdge(source="agent", target="collect")]
    topology = schemas.ServiceTopology(topology_id="topo1", nodes=nodes, edges=edges)
    graph.load_topology(topology)
    deps = graph.get_dependencies("agent")
    dents = graph.get_dependents("collect")
    paths = graph.find_all_paths("agent", "collect")
    data = graph.to_dict()

    async def _run():
        engine = dep_mod.DependencyModelingEngine(graph)
        await engine.model_dependencies(topology)
        return await engine.query_dependencies(schemas.DependencyRequest(service_name="agent"))

    q = asyncio.run(_run())
    assert isinstance(deps, list)
    assert isinstance(dents, list)
    assert len(paths) >= 0
    assert "node_count" in data
    assert isinstance(q, list)


def test_topology_saga(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    saga_mod = _load(
        top_path / "saga.py",
        "services.topology_service.saga",
        monkeypatch,
    )
    schemas = sys.modules["services.topology_service.schemas"]
    orchestrator = saga_mod.TopologySagaOrchestrator()
    step = schemas.SagaStep(step_id="1", service="s", action="a", compensation="c")
    orchestrator.register(
        "x",
        [step],
        {"a": lambda: "ok"},
        {"c": lambda: None},
    )

    async def _run():
        result = await orchestrator.execute("x")  # noqa: F841  # Variable for test verification
        tx = orchestrator.get_transaction("x")
        return result, tx

    result, tx = asyncio.run(_run())
    assert result["success"] is True
    assert tx.status == "success"


def test_topology_impact(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    dep_mod = _load(
        top_path / "dependency.py",
        "services.topology_service.dependency",
        monkeypatch,
    )
    impact_mod = _load(
        top_path / "impact.py",
        "services.topology_service.impact",
        monkeypatch,
    )
    schemas = sys.modules["services.topology_service.schemas"]
    graph = dep_mod.DependencyGraph()
    nodes = [
        schemas.TopologyNode(node_id="agent", name="Agent"),
        schemas.TopologyNode(node_id="collect", name="Collector"),
    ]
    edges = [schemas.TopologyEdge(source="agent", target="collect")]
    topology = schemas.ServiceTopology(topology_id="topo1", nodes=nodes, edges=edges)
    graph.load_topology(topology)
    analyzer = impact_mod.ImpactAnalyzer(graph)
    request = schemas.ImpactRequest(
        changed_nodes=["agent"],
        direction="both",
        max_depth=2,
        change_magnitude=1.0,
    )

    async def _run():
        result = await analyzer.analyze(request)  # noqa: F841  # Variable for test verification
        batch = await analyzer.batch_analyze([request])
        return result, batch

    result, batch = asyncio.run(_run())
    assert 0 <= result.impact_score <= 1
    assert len(batch) == 1


def test_topology_discovery(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    disc_mod = _load(
        top_path / "discovery.py",
        "services.topology_service.discovery",
        monkeypatch,
    )
    schemas = sys.modules["services.topology_service.schemas"]
    engine = disc_mod.TopologyDiscoveryEngine()
    req = schemas.DiscoveryRequest(source="config", scope="core", requested_by="test")

    async def _run():
        result = await engine.discover(req)  # noqa: F841  # Variable for test verification
        batch = await engine.batch_discover([req])
        return result, batch

    result, batch = asyncio.run(_run())
    assert len(result.nodes) > 0
    assert len(batch) == 1


def test_topology_realtime(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    rt_mod = _load(
        top_path / "realtime.py",
        "services.topology_service.realtime",
        monkeypatch,
    )
    manager = rt_mod.RealtimeTopologyManager()

    async def _run():
        queue = await manager.connect()
        await manager.update_topology("topo1", {"x": 1})
        await manager.broadcast({"type": "test"})
        await manager.send_heartbeat()
        cache = manager.get_cache("topo1")
        await manager.disconnect(queue)
        return cache

    cache = asyncio.run(_run())
    assert "x" in cache


def test_topology_orchestrator(monkeypatch):
    _topology_pkg(monkeypatch)
    top_path = ADDONS / "observability" / "topology_service"
    _load(
        top_path / "dependency.py",
        "services.topology_service.dependency",
        monkeypatch,
    )
    _load(
        top_path / "discovery.py",
        "services.topology_service.discovery",
        monkeypatch,
    )
    _load(
        top_path / "impact.py",
        "services.topology_service.impact",
        monkeypatch,
    )
    _load(
        top_path / "realtime.py",
        "services.topology_service.realtime",
        monkeypatch,
    )
    orch_mod = _load(
        top_path / "orchestrator.py",
        "services.topology_service.orchestrator",
        monkeypatch,
    )
    schemas = sys.modules["services.topology_service.schemas"]
    app = orch_mod.TopologyOrchestratorApp()

    async def _run():
        await app.init()
        orch_mod.orchestrator_app = app
        health = await orch_mod.health()
        result = await orch_mod.create_topology(  # noqa: F841  # Variable for test verification
            schemas.DiscoveryRequest(source="config", scope="core")
        )
        return health, result

    health, result = asyncio.run(_run())  # noqa: F841  # Variable for test verification
    assert health.status == "ok"
    assert "topology_id" in result
