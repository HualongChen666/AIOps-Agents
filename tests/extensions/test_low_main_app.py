import ast
import asyncio  # noqa: F401  # Imported for test setup
import importlib.util
import inspect
import sys  # noqa: F401  # Imported for test setup
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup

ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"
FILES = sorted(ROOT.rglob("main_app.py"))
_STD_LIB = getattr(sys, "stdlib_module_names", set())


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
    return mod


def _fake_starlette():
    mod = types.ModuleType("starlette.responses")
    mod.Response = type("Response", (), {"__init__": lambda self, *a, **k: None})
    return mod


def _fake_uvicorn():
    mod = types.ModuleType("uvicorn")
    mod.run = MagicMock()
    return mod


@pytest.fixture(autouse=True)
def _stub_optional_deps(monkeypatch):
    """Stub missing optional dependencies to avoid real I/O."""
    monkeypatch.setitem(sys.modules, "fastapi", _fake_fastapi())
    monkeypatch.setitem(sys.modules, "prometheus_client", _fake_prometheus())
    if "starlette" not in sys.modules:
        monkeypatch.setitem(sys.modules, "starlette", types.ModuleType("starlette"))
    monkeypatch.setitem(sys.modules, "starlette.responses", _fake_starlette())
    monkeypatch.setitem(sys.modules, "uvicorn", _fake_uvicorn())
    for name in ("redis", "httpx", "aiohttp", "grpc"):
        if name not in sys.modules:
            monkeypatch.setitem(sys.modules, name, MagicMock(name=name))


def _magic_mod(monkeypatch, name, is_package=False, path=None):
    if name in sys.modules:
        return sys.modules[name]
    mod = types.ModuleType(name)
    if is_package:
        mod.__path__ = [str(path)] if path else []
        mod.__package__ = name
    else:
        mod.__file__ = f"{name}.py"

    def __getattr__(n):
        if n.startswith("__") and n.endswith("__"):
            raise AttributeError(f"module {name!r} has no attribute {n!r}")
        val = MagicMock(name=f"{name}.{n}")
        mod.__dict__[n] = val
        return val

    mod.__getattr__ = __getattr__
    monkeypatch.setitem(sys.modules, name, mod)
    return mod


def _create_main_stub(monkeypatch):
    mod = types.ModuleType("main")
    mod.app = _FakeApp()
    mod.__getattr__ = lambda n: MagicMock(name=f"main.{n}")
    monkeypatch.setitem(sys.modules, "main", mod)
    return mod


def _stub_siblings(monkeypatch, pkg_name, dir_path):
    pkg = _magic_mod(monkeypatch, pkg_name, is_package=True)
    for item in Path(dir_path).iterdir():
        if item.name.startswith("__") and item.name.endswith("__"):
            continue
        if item.is_file() and item.suffix == ".py" and item.name != "main_app.py":
            child_name = f"{pkg_name}.{item.stem}"
            child = _magic_mod(monkeypatch, child_name)
            pkg.__dict__[item.stem] = child
        elif item.is_dir() and item.name != "__pycache__":
            child_pkg_name = f"{pkg_name}.{item.name}"
            child_pkg = _magic_mod(monkeypatch, child_pkg_name, is_package=True)
            pkg.__dict__[item.name] = child_pkg
            _stub_siblings(monkeypatch, child_pkg_name, item)


def _stub_absolute_imports(monkeypatch, path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and not node.level and node.module:
            top = node.module.split(".")[0]
            if top == "__future__":
                continue
            if top == "main":
                _create_main_stub(monkeypatch)
                continue
            if top != "services" and top in _STD_LIB:
                continue
            parts = node.module.split(".")
            full = parts[0]
            _magic_mod(monkeypatch, full, is_package=len(parts) > 1)
            for i, part in enumerate(parts[1:], start=1):
                full = f"{full}.{part}"
                _magic_mod(monkeypatch, full, is_package=i < len(parts) - 1)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top == "__future__":
                    continue
                if top == "main":
                    _create_main_stub(monkeypatch)
                    continue
                if top != "services" and top in _STD_LIB:
                    continue
                parts = alias.name.split(".")
                full = parts[0]
                _magic_mod(monkeypatch, full, is_package=len(parts) > 1)
                for part in parts[1:]:
                    full = f"{full}.{part}"
                    _magic_mod(monkeypatch, full, is_package=True)


@pytest.mark.parametrize(
    "main_app_path",
    FILES,
    ids=[str(p.relative_to(ROOT)) for p in FILES],
)
def test_main_app_loads(main_app_path, monkeypatch):
    service_dir = main_app_path.parent
    unique_pkg = f"_test_main_app_{FILES.index(main_app_path)}"

    _stub_siblings(monkeypatch, unique_pkg, service_dir)
    _stub_absolute_imports(monkeypatch, main_app_path)

    spec = importlib.util.spec_from_file_location(
        f"{unique_pkg}.main_app",
        str(main_app_path),
    )
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    spec.loader.exec_module(module)

    app_obj = None
    if "create_app" in module.__dict__ and callable(module.__dict__["create_app"]):
        app_obj = module.__dict__["create_app"]()
    elif "get_app" in module.__dict__ and callable(module.__dict__["get_app"]):
        app_obj = module.__dict__["get_app"]()
    elif "app" in module.__dict__:
        app_obj = module.__dict__["app"]

    assert app_obj is not None, f"No app object found in {main_app_path}"

    for fn_name in ("main", "start"):
        fn = module.__dict__.get(fn_name)
        if inspect.isfunction(fn):
            try:
                sig = inspect.signature(fn)
                if all(
                    p.default is not inspect.Parameter.empty
                    or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                    for p in sig.parameters.values()
                ):
                    if inspect.iscoroutinefunction(fn):
                        asyncio.run(fn())
                    else:
                        fn()
            except TypeError:
                pass
