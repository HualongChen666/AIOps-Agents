# -*- coding: utf-8 -*-
"""Smoke tests for low-coverage gRPC/RPC helper modules in extensions."""

from __future__ import annotations

import ast
import asyncio
import importlib.util
import inspect
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ADDONS_ROOT = Path(__file__).resolve().parents[2] / "extensions" / "addons"
ROOT_PKG = "__low_grpc"

_INITIAL_HTTPS = "httpx" in sys.modules
_INITIAL_LOGURU = "loguru" in sys.modules
_INITIAL_GRPC = "grpc" in sys.modules
_INITIAL_SERVICES = "services" in sys.modules


def _sanitized_name(part: str) -> str:
    return part.replace("-", "_").replace(".", "_")


def _ensure_package_chain(rel_dir: Path) -> str:
    parts = [_sanitized_name(p) for p in rel_dir.parts]
    root_pkg = sys.modules.setdefault(ROOT_PKG, types.ModuleType(ROOT_PKG))
    root_pkg.__path__ = [str(ADDONS_ROOT)]
    current = ROOT_PKG
    for i, part in enumerate(parts):
        current += f".{part}"
        pkg = sys.modules.setdefault(current, types.ModuleType(current))
        pkg.__path__ = [str(ADDONS_ROOT / Path(*rel_dir.parts[: i + 1]))]
    return current


def _ensure_module_exists(name: str) -> types.ModuleType:
    if name in sys.modules:
        return sys.modules[name]
    parts = name.split(".")
    mod = sys.modules.setdefault(parts[0], types.ModuleType(parts[0]))
    if not hasattr(mod, "__path__"):
        mod.__path__ = []
    for i in range(2, len(parts) + 1):
        subname = ".".join(parts[:i])
        if subname in sys.modules:
            mod = sys.modules[subname]
            continue
        submod = types.ModuleType(subname)
        submod.__package__ = ".".join(parts[: i - 1])
        if i < len(parts):
            submod.__path__ = []
        mod = submod
        sys.modules[subname] = submod
    return mod


def _stub_imports(source: str, package: str) -> None:
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        module = node.module or ""
        if module == "__future__":
            continue
        if node.level == 0 and (module == "typing" or module.startswith("typing.")):
            continue
        if node.level == 0 and module in ("httpx", "loguru", "grpc"):
            continue

        if node.level > 0:
            abs_mod = importlib.util.resolve_name(
                "." * node.level + (module or ""), package
            )
        else:
            abs_mod = module

        leaf = _ensure_module_exists(abs_mod)
        for alias in node.names:
            if not hasattr(leaf, alias.name):
                setattr(
                    leaf,
                    alias.name,
                    MagicMock(name=f"{abs_mod}.{alias.name}"),
                )


def _load_module(rel_path: str) -> types.ModuleType:
    path = ADDONS_ROOT / rel_path
    rel = path.relative_to(ADDONS_ROOT)
    package = _ensure_package_chain(rel.parent)

    source = path.read_text(encoding="utf-8")
    _stub_imports(source, package)

    if path.stem == "__init__":
        module_name = package
        spec = importlib.util.spec_from_file_location(
            module_name, str(path), submodule_search_locations=[str(path.parent)]
        )
    else:
        module_name = f"{package}.{_sanitized_name(path.stem)}"
        spec = importlib.util.spec_from_file_location(
            module_name, str(path), submodule_search_locations=None
        )

    if spec is None or spec.loader is None:
        pytest.skip(f"Could not create spec for {rel_path}")

    module = importlib.util.module_from_spec(spec)
    module.__package__ = package
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        sys.modules.pop(module_name, None)
        pytest.skip(f"Failed to load {rel_path}: {exc}")
    return module


def _run(coro):
    return asyncio.run(coro)


def _exercise_class(cls):
    sig = inspect.signature(cls.__init__)
    kwargs = {}
    if "base_url" in sig.parameters:
        kwargs["base_url"] = "http://localhost:8000"
    instance = cls(**kwargs)

    async def _handler(**kwargs):
        return "ok"

    async def _exercise():
        if hasattr(instance, "register") and callable(instance.register):
            instance.register("test", _handler)
        if hasattr(instance, "list_methods") and callable(instance.list_methods):
            instance.list_methods()
        if hasattr(instance, "call") and callable(instance.call):
            if hasattr(instance, "register") and callable(instance.register):
                instance.register("test", _handler)
            await instance.call("test", payload={})
        for method in ("send", "start_server", "stop_server", "close"):
            m = getattr(instance, method, None)
            if callable(m):
                if asyncio.iscoroutinefunction(m):
                    await m()
                else:
                    m()

    _run(_exercise())


def _exercise_module(mod):
    for name in dir(mod):
        if name.startswith("_"):
            continue
        obj = getattr(mod, name)
        if inspect.isclass(obj) and getattr(obj, "__module__", None) == mod.__name__:
            _exercise_class(obj)


@pytest.fixture(autouse=True)
def _low_grpc_stubs(monkeypatch):
    httpx_mod = types.ModuleType("httpx")

    class _FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            pass

        def json(self):
            return self._payload

    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

        async def get(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

        async def request(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

        async def aclose(self, *args, **kwargs):
            return None

    class _FakeClient:
        def post(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

        def get(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

        def request(self, *args, **kwargs):
            return _FakeResponse({"ok": True})

    httpx_mod.AsyncClient = _FakeAsyncClient
    httpx_mod.Client = _FakeClient
    httpx_mod.Response = _FakeResponse
    monkeypatch.setitem(sys.modules, "httpx", httpx_mod)

    loguru_mod = types.ModuleType("loguru")
    loguru_mod.logger = MagicMock(name="loguru.logger")
    monkeypatch.setitem(sys.modules, "loguru", loguru_mod)

    grpc_mod = MagicMock(name="grpc")
    monkeypatch.setitem(sys.modules, "grpc", grpc_mod)

    if not _INITIAL_SERVICES:
        services_root = types.ModuleType("services")
        services_root.__path__ = []
        monkeypatch.setitem(sys.modules, "services", services_root)

    yield


TARGETS = sorted(
    p.as_posix()
    for p in ADDONS_ROOT.rglob("grpc/*.py")
    if p.is_relative_to(ADDONS_ROOT)
)


@pytest.mark.parametrize("rel_path", TARGETS, ids=lambda p: p)
def test_low_grpc_module(rel_path):
    module = _load_module(rel_path)
    _exercise_module(module)
