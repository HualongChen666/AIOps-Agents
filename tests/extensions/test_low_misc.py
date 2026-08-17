# -*- coding: utf-8 -*-
"""Smoke tests for the lowest-coverage misc extensions modules."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import sys
import types
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[2]
ADDONS = ROOT / "extensions" / "addons"
STD_LIB = getattr(sys, "stdlib_module_names", set())


def _make_model(name: str):
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self):
        return self.__dict__.copy()

    @classmethod
    def model_validate(cls, data):
        if isinstance(data, dict):
            return cls(**data)
        return data

    def __repr__(self):
        return f"<{name}>"

    return type(
        name,
        (),
        {
            "__init__": __init__,
            "model_dump": model_dump,
            "model_validate": model_validate,
            "__repr__": __repr__,
        },
    )


def _magic_mod(monkeypatch, name: str):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    mod.__path__ = []

    def __getattr__(n):
        if n.startswith("__") and n.endswith("__"):
            raise AttributeError(f"module {name!r} has no attribute {n!r}")
        val = MagicMock(name=f"{name}.{n}")
        mod.__dict__[n] = val
        return val

    mod.__getattr__ = __getattr__
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _ensure_pkg(monkeypatch, name: str, path: Path | None = None):
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


def _stub_siblings(monkeypatch, unique: str, dir_path: Path):
    pkg = _magic_mod(monkeypatch, unique)
    for item in Path(dir_path).iterdir():
        if item.name.startswith("__") and item.name.endswith("__"):
            continue
        if item.is_file() and item.suffix == ".py":
            child_name = f"{unique}.{item.stem}"
            child = _magic_mod(monkeypatch, child_name)
            pkg.__dict__[item.stem] = child
        elif item.is_dir() and item.name != "__pycache__":
            child_pkg_name = f"{unique}.{item.name}"
            child_pkg = _magic_mod(monkeypatch, child_pkg_name)
            pkg.__dict__[item.name] = child_pkg


def _stub_services_imports(monkeypatch, unique: str, path: Path):
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except Exception:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level == 0:
            if not node.module or not node.module.split(".")[0] == "services":
                continue
            module_name = node.module
        else:
            # Only handle relative imports from the unique package.
            base = unique
            if node.level > 1:
                base = unique.rsplit(".", node.level - 1)[0]
            module_name = base if not node.module else f"{base}.{node.module}"
        mod = _magic_mod(monkeypatch, module_name)
        for alias in node.names:
            name = alias.asname or alias.name
            if module_name.endswith(".schemas"):
                setattr(mod, name, _make_model(name))
            elif module_name.endswith(".metrics"):
                setattr(mod, name, MagicMock(name=name))
            elif module_name.endswith(".config") and name == "settings":
                settings = MagicMock()
                settings.use_in_memory = True
                settings.refresh_token_expire_days = 1
                settings.scheduler_poll_interval_seconds = 1
                setattr(mod, name, settings)
            elif name[0].isupper():
                # Service classes (e.g., WorkflowOrchestrator, HealthCheckEngine) return an AsyncMock instance.
                setattr(mod, name, lambda *a, _n=name, **k: AsyncMock(name=_n))
            else:
                # Service functions (e.g., get_repository) are async callables.
                setattr(
                    mod, name, AsyncMock(name=name, return_value=AsyncMock(name=f"{name}_return"))
                )


class _FakeApp:
    def __init__(self, *args, **kwargs):
        pass

    def _route(self, *args, **kwargs):
        return lambda fn: fn

    get = post = put = patch = delete = websocket = on_event = _route

    def __getattr__(self, name):
        return lambda *args, **kwargs: (lambda fn: fn)


class _FakeWebSocket:
    async def accept(self):
        pass

    async def receive_text(self):
        return ""

    async def send_text(self, text):
        pass


def _fake_fastapi():
    mod = types.ModuleType("fastapi")
    mod.FastAPI = _FakeApp
    mod.HTTPException = type("HTTPException", (Exception,), {})
    mod.WebSocket = _FakeWebSocket
    mod.WebSocketDisconnect = type("WebSocketDisconnect", (Exception,), {})
    mod.Body = lambda *args, **kwargs: None
    mod.Depends = lambda *args, **kwargs: None
    mod.status = types.SimpleNamespace(
        HTTP_200_OK=200,
        HTTP_201_CREATED=201,
        HTTP_404_NOT_FOUND=404,
        HTTP_500_INTERNAL_SERVER_ERROR=500,
    )
    mod.APIRouter = _FakeApp
    return mod


def _fake_prometheus():
    mod = types.ModuleType("prometheus_client")
    mod.CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"
    mod.generate_latest = lambda: b""
    mod.REGISTRY = types.SimpleNamespace(register=lambda *a, **k: None)
    return mod


def _fake_starlette():
    if "starlette" not in sys.modules:
        sys.modules["starlette"] = types.ModuleType("starlette")
    mod = types.ModuleType("starlette.responses")
    mod.Response = type("Response", (), {"__init__": lambda self, *a, **k: None})
    return mod


def _fake_loguru():
    mod = types.ModuleType("loguru")
    mod.logger = MagicMock()
    return mod


def _fake_uvicorn():
    mod = types.ModuleType("uvicorn")
    mod.run = MagicMock()
    return mod


def _stub_external(monkeypatch):
    monkeypatch.setitem(sys.modules, "fastapi", _fake_fastapi())
    monkeypatch.setitem(sys.modules, "prometheus_client", _fake_prometheus())
    if "starlette" not in sys.modules:
        monkeypatch.setitem(sys.modules, "starlette", types.ModuleType("starlette"))
    monkeypatch.setitem(sys.modules, "starlette.responses", _fake_starlette())
    monkeypatch.setitem(sys.modules, "loguru", _fake_loguru())
    monkeypatch.setitem(sys.modules, "uvicorn", _fake_uvicorn())
    for name in ("httpx", "requests", "aiohttp", "grpc"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, MagicMock(name=name))
    # Redis: only set the top-level module; keep redis.asyncio absent so cache files fall back to in-memory.
    if "redis" not in sys.modules:
        monkeypatch.setitem(sys.modules, "redis", MagicMock(name="redis"))


def _load(path: Path, unique: str, monkeypatch):
    _ensure_pkg(monkeypatch, unique, path.parent)
    _stub_siblings(monkeypatch, unique, path.parent)
    _stub_services_imports(monkeypatch, unique, path)
    _stub_external(monkeypatch)
    name = f"{unique}.{path.stem}"
    spec = importlib.util.spec_from_file_location(name, str(path))
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {path}")
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def test_infrastructure_config_service_config_manager(monkeypatch):
    path = ADDONS / "infrastructure/config_service/config_manager.py"
    module = _load(path, "_low_misc_0", monkeypatch)
    repo = AsyncMock()
    repo.get_config.return_value = module.ConfigValue(
        config_id="c1", value="old", namespace="ns", updated_by="system"
    )
    repo.list_configs.return_value = [
        module.ConfigValue(config_id="c2", namespace="ns", updated_at=datetime.utcnow())
    ]
    manager = module.ConfigManager(repo)
    asyncio.run(manager.create(module.ConfigValue(config_id="c1", value="v", namespace="ns")))
    asyncio.run(manager.get("c1"))
    asyncio.run(manager.update("c1", "new"))
    asyncio.run(manager.delete("c1"))


def test_observability_topology_service_repository(monkeypatch):
    path = ADDONS / "observability/topology_service/repository.py"
    module = _load(path, "_low_misc_1", monkeypatch)
    repo = module.InMemoryTopologyRepository()
    topology = module.ServiceTopology(topology_id="t1", updated_at=datetime.utcnow())
    asyncio.run(repo.save(topology))
    asyncio.run(repo.get("t1"))
    asyncio.run(repo.count())
    asyncio.run(repo.delete("t1"))


def test_observability_topology_service_visualization(monkeypatch):
    path = ADDONS / "observability/topology_service/visualization.py"
    module = _load(path, "_low_misc_2", monkeypatch)
    viz = module.TopologyVisualizer()
    topology = module.ServiceTopology(
        nodes=[
            module.TopologyNode(
                node_id="n1",
                name="node1",
                node_type="type",
                health="ok",
                x=None,
                y=None,
                metadata={},
            )
        ],
        edges=[
            module.TopologyEdge(source="n1", target="n1", edge_type="type", weight=1, metadata={})
        ],
    )
    config = module.VisualizationConfig(width=800, height=600, layout="force")
    asyncio.run(viz.generate(topology, config))


def test_observability_topology_service_versioning(monkeypatch):
    path = ADDONS / "observability/topology_service/versioning.py"
    module = _load(path, "_low_misc_3", monkeypatch)
    vm = module.TopologyVersionManager()
    topology = module.ServiceTopology(topology_id="top1", updated_at=datetime.utcnow())
    version = asyncio.run(vm.commit(topology, "msg"))
    asyncio.run(vm.list_versions("top1"))
    asyncio.run(vm.compare("top1", version.version, version.version))
    asyncio.run(vm.rollback("top1", version.version))


def test_operations_workflow_service_versioning(monkeypatch):
    path = ADDONS / "operations/workflow_service/versioning.py"
    module = _load(path, "_low_misc_4", monkeypatch)
    vm = module.WorkflowVersionManager()
    definition = module.WorkflowDefinition(workflow_id="wf1", updated_at=datetime.utcnow())
    version = asyncio.run(vm.commit(definition, "msg"))
    asyncio.run(vm.list_versions("wf1"))
    asyncio.run(vm.compare("wf1", version.version, version.version))
    asyncio.run(vm.rollback("wf1", version.version))


def test_infrastructure_config_service_repository(monkeypatch):
    path = ADDONS / "infrastructure/config_service/repository.py"
    module = _load(path, "_low_misc_5", monkeypatch)
    repo = module.InMemoryConfigRepository()
    cfg = module.ConfigValue(config_id="c1", namespace="ns", updated_at=datetime.utcnow())
    asyncio.run(repo.save_config(cfg))
    asyncio.run(repo.get_config("c1"))
    asyncio.run(repo.delete_config("c1"))
    ver = module.ConfigVersion(version_id="v1", namespace="ns", created_at=datetime.utcnow())
    asyncio.run(repo.save_version(ver))
    snap = module.ConfigSnapshot(snapshot_id="s1")
    asyncio.run(repo.save_snapshot(snap))
    entry = module.AuditLogEntry(config_id="c1", log_id="l1")
    asyncio.run(repo.save_audit_log(entry))
    saga = module.SagaTransaction(saga_id="sg1")
    asyncio.run(repo.save_saga(saga))


def test_operations_workflow_service_scheduler_app(monkeypatch):
    path = ADDONS / "operations/workflow_service/scheduler_app.py"
    module = _load(path, "_low_misc_6", monkeypatch)
    app = module.WorkflowSchedulerApp()
    asyncio.run(app.init())


def test_ai_plus_knowledge_graph_service_cache(monkeypatch):
    path = ADDONS / "ai-plus/knowledge_graph_service/cache.py"
    module = _load(path, "_low_misc_7", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_observability_topology_service_analyzer(monkeypatch):
    path = ADDONS / "observability/topology_service/analyzer.py"
    module = _load(path, "_low_misc_8", monkeypatch)
    app = module.TopologyAnalyzerApp()
    asyncio.run(app.init())


def test_operations_workflow_service_executor_app(monkeypatch):
    path = ADDONS / "operations/workflow_service/executor_app.py"
    module = _load(path, "_low_misc_9", monkeypatch)
    app = module.WorkflowExecutorApp()
    asyncio.run(app.init())


def test_observability_topology_service_visualizer_app(monkeypatch):
    path = ADDONS / "observability/topology_service/visualizer_app.py"
    module = _load(path, "_low_misc_10", monkeypatch)
    app = module.TopologyVisualizerApp()
    asyncio.run(app.init())


def test_operations_workflow_service_workflow_orchestrator_app(monkeypatch):
    path = ADDONS / "operations/workflow_service/workflow_orchestrator_app.py"
    module = _load(path, "_low_misc_11", monkeypatch)
    app = module.WorkflowOrchestratorApp()
    asyncio.run(app.init())
    definition = module.WorkflowDefinition(workflow_id="wf1")
    asyncio.run(app.create_definition(definition))


def test_observability_topology_service_saga(monkeypatch):
    path = ADDONS / "observability/topology_service/saga.py"
    module = _load(path, "_low_misc_12", monkeypatch)
    orch = module.TopologySagaOrchestrator()
    step = module.SagaStep(step_id="s1", action="act", compensation="comp", service="svc")
    orch.register("s1", [step], {"act": lambda: "ok"}, {"comp": lambda: None})
    asyncio.run(orch.execute("s1"))


def test_operations_workflow_service_saga(monkeypatch):
    path = ADDONS / "operations/workflow_service/saga.py"
    module = _load(path, "_low_misc_13", monkeypatch)
    orch = module.WorkflowSagaOrchestrator()
    step = module.SagaStep(step_id="s1", action="act", compensation="comp", service="svc")
    orch.register("s1", [step], {"act": lambda: "ok"}, {"comp": lambda: None})
    asyncio.run(orch.execute("s1"))


def test_operations_scenario_memory_service_cache(monkeypatch):
    path = ADDONS / "operations/scenario_memory_service/cache.py"
    module = _load(path, "_low_misc_14", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_infrastructure_config_service_version_control(monkeypatch):
    path = ADDONS / "infrastructure/config_service/version_control.py"
    module = _load(path, "_low_misc_15", monkeypatch)
    repo = AsyncMock()
    repo.list_configs.return_value = [module.ConfigVersion(key="k", value="v")]
    vcc = module.ConfigVersionControl(repo)
    asyncio.run(vcc.commit("ns", "msg"))
    asyncio.run(vcc.list("ns"))


def test_infrastructure_user_service_orchestrator(monkeypatch):
    path = ADDONS / "infrastructure/user_service/orchestrator.py"
    module = _load(path, "_low_misc_16", monkeypatch)
    repo = AsyncMock()
    orch = module.UserOrchestrator(repo)
    data = module.UserCreate(username="u1")
    asyncio.run(orch.create_user(data))
    asyncio.run(orch.create_session("u1"))
    saga = module.SagaTransaction(steps=[module.SagaTransaction(action="create")])
    asyncio.run(orch.run_saga(saga))


def test_infrastructure_config_service_namespace(monkeypatch):
    path = ADDONS / "infrastructure/config_service/namespace.py"
    module = _load(path, "_low_misc_17", monkeypatch)
    repo = AsyncMock()
    nm = module.NamespaceManager(repo)
    asyncio.run(nm.create("ns", "k", "v"))


def test_infrastructure_user_service_saga(monkeypatch):
    path = ADDONS / "infrastructure/user_service/saga.py"
    module = _load(path, "_low_misc_18", monkeypatch)

    async def handler(step):
        return "ok"

    async def comp(step):
        return None

    repo = AsyncMock()
    orch = module.UserSagaOrchestrator(repo)
    saga = module.SagaTransaction(steps=[module.SagaTransaction(action="create")])
    orch.register("create", handler, comp)
    asyncio.run(orch.execute(saga))


def test_infrastructure_user_service_session(monkeypatch):
    path = ADDONS / "infrastructure/user_service/session.py"
    module = _load(path, "_low_misc_19", monkeypatch)
    repo = AsyncMock()
    sm = module.SessionManager(repo)
    asyncio.run(sm.create("u1"))
    asyncio.run(sm.get("s1"))
    asyncio.run(sm.delete("s1"))


def test_observability_topology_service_audit(monkeypatch):
    path = ADDONS / "observability/topology_service/audit.py"
    module = _load(path, "_low_misc_20", monkeypatch)
    store = module.TopologyAuditStore()
    asyncio.run(store.record("t1", "created", "actor", {}))
    asyncio.run(store.get_events("t1"))


def test_infrastructure_config_service_audit_logger(monkeypatch):
    path = ADDONS / "infrastructure/config_service/audit_logger.py"
    module = _load(path, "_low_misc_21", monkeypatch)
    repo = AsyncMock()
    logger = module.ConfigAuditLogger(repo)
    asyncio.run(logger.log("c1", "created", {}))
    asyncio.run(logger.query("c1"))


def test_infrastructure_user_service_audit_logger(monkeypatch):
    path = ADDONS / "infrastructure/user_service/audit_logger.py"
    module = _load(path, "_low_misc_22", monkeypatch)
    repo = AsyncMock()
    logger = module.UserAuditLogger(repo)
    asyncio.run(logger.log("u1", "created", {}))
    asyncio.run(logger.query("u1"))


def test_observability_topology_service_orchestrator(monkeypatch):
    path = ADDONS / "observability/topology_service/orchestrator.py"
    module = _load(path, "_low_misc_23", monkeypatch)
    app = module.TopologyOrchestratorApp()
    asyncio.run(app.init())


def test_engines_doc_policy_engine(monkeypatch):
    path = ADDONS / "engines/doc_policy_engine.py"
    module = _load(path, "_low_misc_24", monkeypatch)
    doc = module.DocEngine()
    doc.build_docs("src", "out")
    policy = module.PolicyEngine()
    policy.lint_openapi({"openapi": "3.0.0", "info": {"title": "t"}, "paths": {}})
    policy.validate_schema(
        {"name": "x"},
        {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]},
    )
    policy.load_config("NOTSET")
    policy.user_lookup("u1")
    policy.plugin_index()
    policy.plugin_load("x")
    policy.plugin_unload("x")


def test_infrastructure_cache_service_cache(monkeypatch):
    path = ADDONS / "infrastructure/cache_service/cache.py"
    module = _load(path, "_low_misc_25", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_infrastructure_data_access_service_cache(monkeypatch):
    path = ADDONS / "infrastructure/data_access_service/cache.py"
    module = _load(path, "_low_misc_26", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_infrastructure_vector_retrieval_service_cache(monkeypatch):
    path = ADDONS / "infrastructure/vector_retrieval_service/cache.py"
    module = _load(path, "_low_misc_27", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_documentation_sphinx_documentation_service_cache(monkeypatch):
    path = ADDONS / "documentation/sphinx_documentation_service/cache.py"
    module = _load(path, "_low_misc_28", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())


def test_infrastructure_ansible_automation_service_cache(monkeypatch):
    path = ADDONS / "infrastructure/ansible_automation_service/cache.py"
    module = _load(path, "_low_misc_29", monkeypatch)
    cm = module.CacheManager()
    asyncio.run(cm.set("k", {"x": 1}))
    asyncio.run(cm.get("k"))
    asyncio.run(cm.delete("k"))
    asyncio.run(cm.clear())
