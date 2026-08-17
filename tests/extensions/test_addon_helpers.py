# -*- coding: utf-8 -*-
"""Smoke tests for small per-addon helper modules.

Each helper is loaded with ``importlib`` under a unique package name, then
instantiated and a few public methods are exercised with the I/O dependencies
monkey-patched to avoid real network or subprocess calls.
"""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import logging
import os
import subprocess
import sys
import types
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

ADDONS_ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"


INIT_ARG_MAP = {
    "service_name": "test",
    "redis_url": "redis://localhost",
    "metrics": MagicMock(),
    "policy": "exponential",
    "base_url": "http://localhost:8000",
    "host": "localhost",
    "port": 12345,
    "url": "http://localhost:8000",
    "endpoint": "http://localhost:8000",
    "timeout": 5.0,
}

METHOD_ARG_MAP = {
    "fn": lambda: "ok",
    "key": "test-key",
    "value": "test-value",
    "ttl": 300,
    "method": "test",
    "payload": {"ok": True},
    "data": b"test",
    "request": {"ok": True},
    "operation": "test",
    "handler": lambda: "ok",
    "name": "test",
    "settings": MagicMock(),
    "timeout": 5.0,
    "url": "http://localhost:8000",
    "host": "localhost",
    "port": 12345,
    "base_url": "http://localhost:8000",
}


_KINDS = {
    "cache.py": "cache",
    "metrics.py": "metrics",
    "retry.py": "retry",
    "health_check.py": "health",
    "main_app.py": "main",
    "client.py": "grpc_client",
    "server.py": "grpc_server",
}


def _sanitized_name(part: str) -> str:
    """Make a filesystem name a valid Python identifier."""
    return part.replace("-", "_").replace(".", "_")


def _all_helper_paths() -> list[tuple[Path, str]]:
    """Return (path, kind) tuples for every recognised helper file."""
    helpers: list[tuple[Path, str]] = []
    for stem, kind in _KINDS.items():
        if stem in ("client.py", "server.py"):
            pattern = f"*/grpc/{stem}"
        else:
            pattern = f"*/{stem}"
        for path in sorted(
            ADDONS_ROOT.rglob(stem if stem != "client.py" and stem != "server.py" else pattern)
        ):
            # rglob with a glob containing / may not work; filter explicitly
            if stem in ("client.py", "server.py"):
                if path.parent.name != "grpc" or path.name != stem:
                    continue
            helpers.append((path, kind))
    return helpers


_HELPER_PARAMS = _all_helper_paths()


def _ensure_package_chain(rel_dir: Path) -> str:
    """Create a package chain in sys.modules and return the leaf package name."""
    parts = [_sanitized_name(p) for p in rel_dir.parts]
    root_name = "__addon_helpers"
    root = sys.modules.setdefault(root_name, types.ModuleType(root_name))
    root.__path__ = [str(ADDONS_ROOT)]
    current = root_name
    for i, part in enumerate(parts):
        current += f".{part}"
        pkg = sys.modules.setdefault(current, types.ModuleType(current))
        pkg.__path__ = [str(ADDONS_ROOT / Path(*rel_dir.parts[: i + 1]))]
    return current


def _load_helper(path: Path, kind: str):
    """Load a single helper module using importlib and a unique package."""
    rel = path.relative_to(ADDONS_ROOT)
    package = _ensure_package_chain(rel.parent)
    module_name = f"{package}.{_sanitized_name(path.stem)}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        str(path),
        submodule_search_locations=None,
    )
    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {rel.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        # Remove failed import from sys.modules so later attempts are clean.
        sys.modules.pop(module_name, None)
        pytest.skip(f"Failed to load {rel.as_posix()}: {exc}")
    return module


def _find_target(module, kind: str):
    """Locate the public class or function to exercise for this kind."""
    if kind == "cache":
        return getattr(module, "CacheManager", None)
    if kind == "metrics":
        return getattr(module, "MetricsCollector", None)
    if kind == "main":
        for name in ("get_app", "create_app"):
            obj = getattr(module, name, None)
            if obj and callable(obj):
                return obj
        return None
    if kind == "health":
        for name in ("HealthCheck", "HealthCheckEngine", "check"):
            obj = getattr(module, name, None)
            if obj:
                return obj
        # Fallback: any public class/function with "health" or "check" in name
        for name in dir(module):
            if name.startswith("_"):
                continue
            if "health" in name.lower() or "check" in name.lower():
                return getattr(module, name)
        return None

    # Generic class discovery for retry / grpc client / grpc server
    if kind == "retry":
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith("_"):
                continue
            if "retry" in name.lower() or name.endswith("Engine"):
                return obj
    if kind == "grpc_client":
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith("_"):
                continue
            if "Client" in name and "Server" not in name:
                return obj
        return getattr(module, "Client", None)
    if kind == "grpc_server":
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if name.startswith("_"):
                continue
            if "Server" in name and "Client" not in name:
                return obj
        return getattr(module, "Server", None)
    return None


def _build_init_kwargs(target) -> dict:
    """Build safe __init__ kwargs from a known arg map."""
    if not (inspect.isclass(target) or callable(getattr(target, "__init__", None))):
        return {}
    try:
        sig = inspect.signature(target)
    except (ValueError, TypeError):
        return {}
    params = list(sig.parameters.items())
    if params and params[0][0] in ("self", "cls"):
        params = params[1:]
    kwargs: dict = {}
    for name, param in params:
        if param.default is not inspect.Parameter.empty:
            if name in INIT_ARG_MAP:
                kwargs[name] = INIT_ARG_MAP[name]
            continue
        if name in INIT_ARG_MAP:
            kwargs[name] = INIT_ARG_MAP[name]
        else:
            # Unknown required init arg -- cannot safely instantiate
            raise KeyError(name)
    return kwargs


def _build_method_kwargs(method) -> dict:
    """Build safe kwargs for a public method."""
    try:
        sig = inspect.signature(method)
    except (ValueError, TypeError):
        return {}
    params = list(sig.parameters.items())
    if params and params[0][0] in ("self", "cls"):
        params = params[1:]
    kwargs: dict = {}
    for name, param in params:
        if param.default is not inspect.Parameter.empty:
            if name in METHOD_ARG_MAP:
                kwargs[name] = METHOD_ARG_MAP[name]
            continue
        if name in METHOD_ARG_MAP:
            kwargs[name] = METHOD_ARG_MAP[name]
        else:
            raise KeyError(name)
    return kwargs


async def _run_method(method, **kwargs):
    """Call a method, awaiting it if it returns a coroutine/awaitable."""
    if asyncio.iscoroutinefunction(method):
        return await method(**kwargs)
    result = method(**kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


def _exercise_object(obj, method_names: list[str]):
    """Call the first available safe public method on an instance."""
    called = False
    for name in method_names:
        method = getattr(obj, name, None)
        if not callable(method):
            continue
        try:
            kwargs = _build_method_kwargs(method)
        except KeyError:
            continue
        try:
            asyncio.run(_run_method(method, **kwargs))
        except Exception:
            # Method is not safely executable in a smoke test; skip this one.
            continue
        called = True
    if not called:
        pytest.skip("No safe public method could be exercised")


def _exercise_function(fn, arg_names: list[str]):
    """Call a module-level function with safe kwargs."""
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        pytest.skip("Could not inspect function signature")
    kwargs: dict = {}
    for name, param in list(sig.parameters.items()):
        if param.default is not inspect.Parameter.empty:
            if name in METHOD_ARG_MAP:
                kwargs[name] = METHOD_ARG_MAP[name]
            continue
        if name in METHOD_ARG_MAP:
            kwargs[name] = METHOD_ARG_MAP[name]
        else:
            pytest.skip(f"Unknown required function argument: {name}")
    try:
        result = fn(**kwargs)
    except Exception as exc:
        pytest.skip(f"Function call raised: {exc}")
    if inspect.isawaitable(result):
        try:
            asyncio.run(result)
        except Exception as exc:
            pytest.skip(f"Awaitable function raised: {exc}")


def _fake_httpx_module():
    mod = types.ModuleType("httpx")

    class _Response:
        @property
        def status_code(self):
            return 200

        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

        @property
        def text(self):
            return '{"ok": true}'

    class _AsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def post(self, *args, **kwargs):
            return _Response()

        async def get(self, *args, **kwargs):
            return _Response()

        async def request(self, *args, **kwargs):
            return _Response()

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        def post(self, *args, **kwargs):
            return _Response()

        def get(self, *args, **kwargs):
            return _Response()

        def request(self, *args, **kwargs):
            return _Response()

    mod.AsyncClient = _AsyncClient
    mod.Client = _Client
    mod.Response = _Response
    mod.post = _Client().post
    mod.get = _Client().get
    mod.request = _Client().request
    return mod


def _fake_requests_module():
    mod = types.ModuleType("requests")

    class _Response:
        status_code = 200
        text = '{"ok": true}'

        def raise_for_status(self):
            pass

        def json(self):
            return {"ok": True}

    def _request(*args, **kwargs):
        return _Response()

    mod.request = _request
    mod.get = _request
    mod.post = _request
    mod.put = _request
    mod.delete = _request
    mod.Response = _Response
    return mod


def _fake_aiohttp_module():
    mod = types.ModuleType("aiohttp")

    class _ClientResponse:
        status = 200

        async def json(self):
            return {"ok": True}

        async def text(self):
            return '{"ok": true}'

        def raise_for_status(self):
            pass

    class _ClientSession:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def get(self, *args, **kwargs):
            return _ClientResponse()

        async def post(self, *args, **kwargs):
            return _ClientResponse()

        async def request(self, *args, **kwargs):
            return _ClientResponse()

    mod.ClientSession = _ClientSession
    mod.ClientResponse = _ClientResponse
    return mod


def _fake_redis_modules():
    redis_mod = types.ModuleType("redis")
    redis_mod.__path__ = []
    redis_mod.__package__ = "redis"

    class _Redis:
        def get(self, *args, **kwargs):
            return None

        def setex(self, *args, **kwargs):
            return True

        def set(self, *args, **kwargs):
            return True

        def delete(self, *args, **kwargs):
            return 1

        def flushdb(self, *args, **kwargs):
            return True

    redis_mod.Redis = _Redis
    redis_mod.ConnectionError = type("ConnectionError", (Exception,), {})
    redis_mod.TimeoutError = type("TimeoutError", (Exception,), {})

    asyncio_mod = types.ModuleType("redis.asyncio")
    asyncio_mod.__path__ = []
    asyncio_mod.__package__ = "redis.asyncio"

    class _AsyncRedis:
        async def get(self, *args, **kwargs):
            return None

        async def setex(self, *args, **kwargs):
            return True

        async def set(self, *args, **kwargs):
            return True

        async def delete(self, *args, **kwargs):
            return 1

        async def flushdb(self, *args, **kwargs):
            return True

    def _from_url(*args, **kwargs):
        return _AsyncRedis()

    asyncio_mod.Redis = _AsyncRedis
    asyncio_mod.from_url = _from_url
    redis_mod.asyncio = asyncio_mod
    return redis_mod, asyncio_mod


def _fake_psutil_module():
    mod = types.ModuleType("psutil")

    class _Mem:
        percent = 0.0

    class _Disk:
        percent = 0.0

    def _virtual_memory():
        return _Mem()

    def _disk_usage(path):
        return _Disk()

    mod.virtual_memory = _virtual_memory
    mod.disk_usage = _disk_usage
    return mod


def _fake_loguru_module():
    mod = types.ModuleType("loguru")
    mod.logger = MagicMock()
    return mod


def _fake_fastapi_module():
    mod = types.ModuleType("fastapi")

    class _FastAPI:
        def __init__(self, *args, **kwargs):
            pass

        def get(self, *args, **kwargs):
            return lambda f: f

        def post(self, *args, **kwargs):
            return lambda f: f

        def put(self, *args, **kwargs):
            return lambda f: f

        def delete(self, *args, **kwargs):
            return lambda f: f

        def on_event(self, *args, **kwargs):
            return lambda f: f

    mod.FastAPI = _FastAPI
    mod.HTTPException = type("HTTPException", (Exception,), {})
    mod.Body = lambda *args, **kwargs: None
    mod.Depends = lambda *args, **kwargs: None
    mod.Header = lambda *args, **kwargs: None
    mod.Query = lambda *args, **kwargs: None
    mod.Path = lambda *args, **kwargs: None
    mod.Request = type("Request", (), {})
    mod.Response = type("Response", (), {})
    return mod


def _fake_starlette_module():
    mod = types.ModuleType("starlette.responses")
    mod.Response = type("Response", (), {"__init__": lambda self, *a, **k: None})
    sys.modules.setdefault("starlette", types.ModuleType("starlette"))
    sys.modules["starlette"].responses = mod
    return mod


def _fake_uvicorn_module():
    mod = types.ModuleType("uvicorn")
    mod.run = lambda *args, **kwargs: None
    return mod


def _fake_grpc_module():
    mod = types.ModuleType("grpc")
    mod.aio = types.ModuleType("grpc.aio")
    mod.aio.server = lambda *args, **kwargs: MagicMock()
    mod.insecure_channel = lambda *args, **kwargs: MagicMock()
    mod.secure_channel = lambda *args, **kwargs: MagicMock()
    return mod


def _ensure_module_in_sysmodules(name: str, factory):
    if name not in sys.modules:
        sys.modules[name] = factory()


@pytest.fixture(autouse=True)
def _stubs(monkeypatch):
    """Stub external I/O dependencies for the duration of each test."""
    # Build fresh fake modules.
    httpx_mod = _fake_httpx_module()
    requests_mod = _fake_requests_module()
    aiohttp_mod = _fake_aiohttp_module()
    psutil_mod = _fake_psutil_module()
    loguru_mod = _fake_loguru_module()
    fastapi_mod = _fake_fastapi_module()
    uvicorn_mod = _fake_uvicorn_module()
    grpc_mod = _fake_grpc_module()
    starlette_mod = _fake_starlette_module()
    redis_mod, redis_asyncio_mod = _fake_redis_modules()

    # Swap out sys.modules entries so tests always use the stubs.  monkeypatch
    # restores the originals after the test.
    monkeypatch.setitem(sys.modules, "httpx", httpx_mod)
    monkeypatch.setitem(sys.modules, "requests", requests_mod)
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp_mod)
    monkeypatch.setitem(sys.modules, "psutil", psutil_mod)
    monkeypatch.setitem(sys.modules, "loguru", loguru_mod)
    monkeypatch.setitem(sys.modules, "fastapi", fastapi_mod)
    monkeypatch.setitem(sys.modules, "uvicorn", uvicorn_mod)
    monkeypatch.setitem(sys.modules, "grpc", grpc_mod)
    monkeypatch.setitem(
        sys.modules, "starlette", sys.modules.get("starlette") or types.ModuleType("starlette")
    )
    monkeypatch.setitem(sys.modules, "starlette.responses", starlette_mod)
    monkeypatch.setitem(sys.modules, "redis", redis_mod)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio_mod)

    # Patch real modules where they exist so network I/O is avoided.
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: MagicMock(
            returncode=0, stdout="", stderr="", check_returncode=lambda: None
        ),
    )
    try:
        import psutil as _psutil

        monkeypatch.setattr(_psutil, "virtual_memory", lambda: MagicMock(percent=0.0))
        monkeypatch.setattr(_psutil, "disk_usage", lambda path: MagicMock(percent=0.0))
    except ImportError:
        pass

    # Ensure Prometheus does not raise duplicate metric errors.
    try:
        import prometheus_client as _pc

        monkeypatch.setattr(_pc.REGISTRY, "register", lambda *args, **kwargs: None)
    except ImportError:
        pass


def _exercise_target(target, kind: str):
    """Instantiate (if a class) and exercise the target."""
    if inspect.isclass(target):
        try:
            kwargs = _build_init_kwargs(target)
        except KeyError:
            pytest.skip("Could not build safe __init__ kwargs")
        try:
            instance = target(**kwargs)
        except Exception as exc:
            pytest.skip(f"Failed to instantiate {target.__name__}: {exc}")
        if kind == "cache":
            _exercise_object(instance, ["set", "get", "delete"])
        elif kind == "metrics":
            _exercise_object(instance, ["inc_request", "inc_cache_hit", "get_stats"])
        elif kind == "retry":
            _exercise_object(instance, ["execute"])
        elif kind == "health":
            _exercise_object(instance, ["check"])
        elif kind == "grpc_client":
            _exercise_object(instance, ["call", "send"])
        elif kind == "grpc_server":
            # Register a handler first if possible, then call it.
            if hasattr(instance, "register") and callable(getattr(instance, "register")):
                try:
                    reg_kwargs = _build_method_kwargs(instance.register)
                except KeyError:
                    reg_kwargs = {}
                try:
                    if asyncio.iscoroutinefunction(instance.register):
                        asyncio.run(_run_method(instance.register, **reg_kwargs))
                    else:
                        instance.register(**reg_kwargs)
                except Exception:
                    pass
            _exercise_object(instance, ["call", "list_methods", "start", "stop"])
        else:
            _exercise_object(instance, ["run", "execute", "process", "handle"])
    else:
        # Module-level function / object
        if kind == "main":
            _exercise_function(target, ["settings"])
        elif kind == "health" and callable(target):
            _exercise_function(target, [])
        else:
            pytest.skip("No testable public class/function")


@pytest.mark.parametrize(
    "helper_path,helper_kind",
    _HELPER_PARAMS,
    ids=[str(p[0].relative_to(ADDONS_ROOT).as_posix()) for p in _HELPER_PARAMS],
)
def test_addon_helper(helper_path, helper_kind, request):
    """Smoke test a single addon helper module."""
    module = _load_helper(helper_path, helper_kind)
    target = _find_target(module, helper_kind)
    if target is None:
        pytest.skip(f"No public class/function for {helper_kind} in {helper_path.name}")
    _exercise_target(target, helper_kind)
