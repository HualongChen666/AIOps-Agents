import asyncio  # noqa: F401  # Imported for test setup
import builtins
import importlib.util
import inspect
import pathlib
import re
import sys  # noqa: F401  # Imported for test setup
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

real_import = __import__

REPO = pathlib.Path(__file__).resolve().parents[2]

SELECTED = [
    r"extensions\addons\observability\topology_service\saga.py",
    r"extensions\addons\operations\workflow_service\saga.py",
    r"extensions\addons\operations\workflow_service\scheduler_app.py",
    r"extensions\addons\observability\topology_service\visualizer_app.py",
    r"extensions\addons\operations\workflow_service\executor_app.py",
    r"extensions\addons\observability\topology_service\analyzer.py",
    r"extensions\addons\infrastructure\user_service\saga.py",
    r"extensions\addons\operations\workflow_service\workflow_orchestrator_app.py",
    r"extensions\addons\observability\topology_service\repository.py",
    r"extensions\addons\observability\topology_service\orchestrator.py",
    r"extensions\addons\engines\doc_policy_engine.py",
    r"extensions\addons\ai-plus\knowledge_graph_service\graph_store.py",
    r"extensions\addons\operations\incident_response_service\service.py",
    r"extensions\addons\operations\scenario_memory_service\orchestrator.py",
    r"extensions\hardware_remediation\ticket_integration.py",
    r"extensions\addons\engines\monitoring_provider.py",
    r"extensions\addons\observability\topology_service\discovery.py",
    r"extensions\hardware_remediation\redfish_actions.py",
    r"extensions\addons\engines\infra_executor.py",
    r"extensions\addons\ai-plus\knowledge_graph_service\modeler.py",
    r"extensions\addons\ai-plus\rag_service\orchestrator.py",
    r"extensions\addons\operations\workflow_service\orchestrator.py",
    r"extensions\addons\ai-plus\llm_router_service\grpc\client.py",
    r"extensions\addons\infrastructure\config_service\grpc\client.py",
    r"extensions\addons\infrastructure\user_service\grpc\client.py",
    r"extensions\addons\observability\topology_service\grpc\client.py",
    r"extensions\addons\operations\workflow_service\grpc\client.py",
    r"extensions\addons\ai-plus\llm_router_service\orchestrator.py",
]


class Fake:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __getattr__(self, name):
        return Fake()

    def __call__(self, *args, **kwargs):
        return Fake(**kwargs)

    def __iter__(self):
        yield Fake()

    def __getitem__(self, key):
        return Fake()

    def __setitem__(self, key, value):
        pass

    def keys(self):
        return []

    def values(self):
        return iter([Fake()])

    def items(self):
        return iter([("key", Fake())])

    def get(self, *args, **kwargs):
        return Fake()

    def __contains__(self, x):
        return True

    def __len__(self):
        return 1

    def __bool__(self):
        return True

    def __int__(self):
        return 0

    def __float__(self):
        return 0.0

    def __index__(self):
        return 0

    def __bytes__(self):
        return b""

    def __fspath__(self):
        return str(self)

    def __str__(self):
        return "fake"

    def __repr__(self):
        return "Fake()"

    def __format__(self, fmt):
        return str(self)

    def __await__(self):
        if 0:
            yield self
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return None

    def __add__(self, other):
        return Fake()

    __radd__ = __add__

    def __sub__(self, other):
        return Fake()

    __rsub__ = __sub__

    def __mul__(self, other):
        return Fake()

    __rmul__ = __mul__

    def __truediv__(self, other):
        return Fake()

    __rtruediv__ = __truediv__

    def __pow__(self, other):
        return Fake()

    __rpow__ = __pow__

    def __lt__(self, other):
        return Fake()

    def __le__(self, other):
        return Fake()

    def __gt__(self, other):
        return Fake()

    def __ge__(self, other):
        return Fake()

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return hash(str(self))

    def __floordiv__(self, other):
        return Fake()

    __rfloordiv__ = __floordiv__

    def __mod__(self, other):
        return Fake()

    __rmod__ = __mod__

    def __or__(self, other):
        return Fake()

    __ror__ = __or__

    def __and__(self, other):
        return Fake()

    __rand__ = __and__

    def __xor__(self, other):
        return Fake()

    __rxor__ = __xor__

    def __neg__(self):
        return Fake()

    def __pos__(self):
        return Fake()

    def __abs__(self):
        return Fake()

    def __invert__(self):
        return Fake()


class FakeFastAPI:
    def __init__(self, *args, **kwargs):
        pass

    def get(self, path, **kwargs):
        return lambda fn: fn

    def post(self, path, **kwargs):
        return lambda fn: fn

    def put(self, path, **kwargs):
        return lambda fn: fn

    def delete(self, path, **kwargs):
        return lambda fn: fn

    def patch(self, path, **kwargs):
        return lambda fn: fn

    def websocket(self, path, **kwargs):
        return lambda fn: fn

    @property
    def state(self):
        return Fake()


_WebSocketDisconnect = type("WebSocketDisconnect", (Exception,), {})

ALLOWED = {
    "abc",
    "asyncio",
    "collections",
    "contextlib",
    "copy",
    "datetime",
    "enum",
    "functools",
    "hashlib",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "logging",
    "math",
    "numbers",
    "os",
    "pathlib",
    "re",
    "shlex",
    "string",
    "sys",
    "time",
    "traceback",
    "types",
    "uuid",
    "warnings",
}

_FAKE_CACHE = {}
_FAKE_CACHE["fastapi"] = Fake()
_FAKE_CACHE["fastapi"].FastAPI = FakeFastAPI
_FAKE_CACHE["fastapi"].WebSocket = Fake
_FAKE_CACHE["fastapi"].WebSocketDisconnect = _WebSocketDisconnect


def _get_fake(key):
    if key not in _FAKE_CACHE:
        _FAKE_CACHE[key] = Fake()
    return _FAKE_CACHE[key]


def fake_import(name, globals=None, locals=None, fromlist=(), level=0, *args):
    if level == 0 and name in ALLOWED:
        return real_import(name, globals, locals, fromlist, level)
    key = name if level == 0 else f"relative_{name}_{level}"
    mod = _get_fake(key)
    if fromlist:
        for attr in fromlist:
            if key == "fastapi":
                if attr == "FastAPI":
                    mod.FastAPI = FakeFastAPI
                elif attr == "WebSocket":
                    mod.WebSocket = Fake
                elif attr == "WebSocketDisconnect":
                    mod.WebSocketDisconnect = _WebSocketDisconnect
            else:
                # Fake __getattr__ already makes every attribute available,
                # but materialising from-list names avoids any getattr surprises.
                if not hasattr(mod, attr):
                    setattr(mod, attr, Fake())
    return mod


def _make_repo():
    repo = AsyncMock()
    repo.get_definition = AsyncMock(
        return_value=SimpleNamespace(
            metadata={},
            nodes=[SimpleNamespace(node_id="n1", dependencies=[])],
        )
    )
    repo.get_task = AsyncMock(return_value=None)
    repo.list_tasks = AsyncMock(return_value=[])
    repo.save_task = AsyncMock(return_value=None)
    repo.save_saga = AsyncMock(return_value=None)
    return repo


def _make_request():
    return Fake(
        workflow_id="wf1",
        params={},
        priority=Fake(value="normal"),
        id="r1",
        json=Fake(),
        content="hello world",
        document_id="doc1",
        metadata={},
        query="hello",
        source=Fake(value="web"),
        event=Fake(),
        messages=[],
        requested_by="test",
        scope="all",
        context="This is a sample context.",
        candidates=[Fake(content="hello world")],
        entity_name="hello",
        entity_type="thing",
        properties={},
        documents=[Fake(content="hello world", document_id="doc1")],
    )


def _make_task():
    return Fake(
        task_id="t1",
        workflow_id="w1",
        completed_nodes=[],
        failed_nodes=[],
        params={},
        status=None,
    )


def _make_saga():
    return Fake(
        steps=[Fake(action="create_user", status=None, result=None)],
        status=None,
    )


def _make_steps():
    return [Fake(action="create_user", compensation="compensation", step_id="s1")]


def _make_documents():
    return [
        Fake(
            content="hello world",
            document_id="doc1",
            metadata={},
            source=Fake(value="web"),
            updated_at=None,
        )
    ]


def _make_execution():
    return Fake(workflow_id="w1", payload={})


def _make_requests():
    return [Fake()]


SENSIBLE = {
    "action": "create_user",
    "actions": {"create_user": Fake(), "compensation": Fake()},
    "api_client": _make_repo,
    "args": ["-l"],
    "base_url": "http://localhost:8000",
    "body": Fake,
    "cache": Fake,
    "command": "echo",
    "compensations": {"compensation": Fake()},
    "completed_nodes": [],
    "config": Fake,
    "data": {},
    "description": "description",
    "documents": _make_documents,
    "dry_run": True,
    "edge": Fake,
    "edge_id": "e1",
    "embedding_model": None,
    "event": Fake,
    "execution": _make_execution,
    "exp": Fake,
    "failed_nodes": [],
    "host": "localhost",
    "incident": Fake,
    "key": "nonexistent_key",
    "instance": {"foo": "bar"},
    "kubectl_args": ["get", "pods"],
    "label": "service",
    "method": "list_methods",
    "metric": "up",
    "model_configs": None,
    "name": "list_methods",
    "namespace": "default",
    "neo4j_password": None,
    "neo4j_uri": None,
    "neo4j_user": None,
    "node": Fake,
    "node_id": "n1",
    "node_type": "service",
    "output_dir": "out",
    "params": {},
    "password": "secret",
    "payload": {},
    "priority": SimpleNamespace(value="normal"),
    "query": "test query",
    "repo": _make_repo,
    "repository": _make_repo,
    "request": _make_request,
    "requested_by": "test",
    "requests": _make_requests,
    "texts": ["hello"],
    "retry_engine": Fake,
    "saga": _make_saga,
    "saga_id": "s1",
    "schema": {"type": "object"},
    "scope": "all",
    "server": Fake,
    "settings": Fake,
    "settings_obj": Fake,
    "source": "api",
    "source_dir": "src",
    "spec": {"openapi": "3.0.0", "info": {"title": "t"}},
    "start": "2020-01-01T00:00:00Z",
    "status": None,
    "step": "1m",
    "steps": _make_steps,
    "summary": "summary",
    "target": "http://prometheus",
    "task": _make_task,
    "task_id": "t1",
    "text": "test text",
    "tool": "jira",
    "username": "root",
    "vector_dimension": 384,
    "websocket": Fake,
    "workflow_id": "wf1",
}


def get_arg(name):
    if name not in SENSIBLE:
        return Fake()
    val = SENSIBLE[name]
    if callable(val):
        return val()
    return val


def build_args(callable_obj):
    if callable_obj is object.__init__:
        return [], {}
    sig = inspect.signature(callable_obj)
    args = []
    kwargs = {}
    for param in sig.parameters.values():
        if param.name in ("self", "cls"):
            continue
        kind = param.kind
        if kind == inspect.Parameter.VAR_POSITIONAL:
            continue
        elif kind == inspect.Parameter.VAR_KEYWORD:
            continue
        elif kind == inspect.Parameter.KEYWORD_ONLY:
            if param.default is inspect.Parameter.empty or param.name in SENSIBLE:
                kwargs[param.name] = get_arg(param.name)
        else:
            args.append(get_arg(param.name))
    return args, kwargs


def call_public(callable_obj):
    args, kwargs = build_args(callable_obj)
    if inspect.iscoroutinefunction(callable_obj):
        asyncio.run(callable_obj(*args, **kwargs))
    else:
        callable_obj(*args, **kwargs)


def find_main(module, module_name, relpath):
    classes = [
        obj
        for obj in module.__dict__.values()
        if inspect.isclass(obj)
        and getattr(obj, "__module__", "") == module_name
        and not inspect.isabstract(obj)
    ]
    funcs = [
        obj
        for obj in module.__dict__.values()
        if inspect.isfunction(obj)
        and not obj.__name__.startswith("_")
        and getattr(obj, "__module__", "") == module_name
    ]
    main_class = None
    if classes:
        stem = pathlib.Path(relpath).stem.replace("-", "_").lower().replace("_", "")

        def score(c):
            return len(
                [m for n, m in inspect.getmembers(c, inspect.isroutine) if not n.startswith("_")]
            )

        best_score = max(score(c) for c in classes)
        candidates = [c for c in classes if score(c) == best_score]
        for c in candidates:
            class_name = c.__name__.lower().replace("_", "")
            if stem in class_name or class_name in stem:
                main_class = c
                break
        else:
            main_class = candidates[0]
    return main_class, funcs


@pytest.mark.parametrize("relpath", SELECTED)
def test_ext_misc(relpath, monkeypatch):
    abs_path = REPO / relpath
    module_name = "ext_" + re.sub(r"[^0-9A-Za-z_]", "_", relpath.replace(".py", ""))
    spec = importlib.util.spec_from_file_location(module_name, str(abs_path))
    module = importlib.util.module_from_spec(spec)

    for mod in list(sys.modules):
        if mod.startswith(
            (
                "services.",
                "sentence_transformers",
                "huggingface_hub",
                "langchain",
                "langchain_openai",
                "openai",
            )
        ):
            del sys.modules[mod]

    builtins.__import__ = fake_import
    try:
        spec.loader.exec_module(module)

        monkeypatch.setattr("sys.argv", ["prog", "jira", "summary", "description"])

        main_class, main_funcs = find_main(module, module_name, relpath)

        if main_class:
            init_args, init_kwargs = build_args(main_class.__init__)
            obj = main_class(*init_args, **init_kwargs)
            if main_class.__name__ == "LLMRouterOrchestrator":
                obj.providers["fake"] = Fake()
            elif main_class.__name__ == "ScenarioMemoryOrchestrator":
                obj.settings = SimpleNamespace(
                    service_name="scenario",
                    short_term_capacity=1000,
                    long_term_capacity=1000,
                    default_cache_ttl=60,
                    max_similar_results=10,
                    similarity_threshold=0.0,
                    embedding_dimension=128,
                    experience_decay_rate=0.1,
                )
            elif main_class.__name__ == "TopologyVisualizerApp":
                obj.realtime = Fake(
                    connect=AsyncMock(
                        return_value=AsyncMock(get=AsyncMock(side_effect=_WebSocketDisconnect))
                    ),
                    disconnect=AsyncMock(),
                )
            elif main_class.__name__ == "RAGOrchestrator":
                obj.langchain = Fake(split=lambda text, *args, **kwargs: [text])
            routines = [
                (name, method)
                for name, method in inspect.getmembers(main_class, inspect.isroutine)
                if not name.startswith("_")
            ]
            routines.sort(
                key=lambda item: getattr(getattr(item[1], "__code__", None), "co_firstlineno", 0)
            )
            for method_name, _ in routines:
                bound = getattr(obj, method_name)
                call_public(bound)

        for func in main_funcs:
            if "websocket" in func.__name__:
                continue
            call_public(func)
    finally:
        builtins.__import__ = real_import
