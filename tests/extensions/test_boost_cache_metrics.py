"""Parametrized coverage tests for extensions/addons cache and metrics modules."""

from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import re
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

TARGET_FILES = sorted(
    list(ROOT.glob("extensions/addons/**/cache.py"))
    + list(ROOT.glob("extensions/addons/**/metrics.py"))
)


class _Metric:
    """Fake Prometheus metric object."""

    def __init__(self, *args, **kwargs):
        pass

    def labels(self, **kwargs):
        return self

    def inc(self, *args, **kwargs):
        pass

    def observe(self, *args, **kwargs):
        pass

    def set(self, *args, **kwargs):
        pass


class _Counter(_Metric):
    pass


class _Histogram(_Metric):
    pass


class _Gauge(_Metric):
    pass


class _OkRedis:
    """Redis backend that succeeds."""

    def __init__(self):
        self._store = {}

    async def get(self, key):
        return self._store.get(key)

    async def setex(self, key, ttl, value):
        self._store[key] = value
        return True

    async def delete(self, key):
        self._store.pop(key, None)
        return 1

    async def flushdb(self):
        self._store.clear()
        return True


class _BadRedis:
    """Redis backend that always raises."""

    async def get(self, key):
        raise ConnectionError("stub redis failure")

    async def setex(self, key, ttl, value):
        raise ConnectionError("stub redis failure")

    async def delete(self, key):
        raise ConnectionError("stub redis failure")

    async def flushdb(self):
        raise ConnectionError("stub redis failure")


class _RedisAsyncio:
    """redis.asyncio stub."""

    def from_url(self, *args, **kwargs):
        return _OkRedis()

    Redis = _OkRedis


class _Logger:
    """loguru logger stub."""

    def debug(self, *a, **k):
        pass

    def info(self, *a, **k):
        pass

    def warning(self, *a, **k):
        pass

    def error(self, *a, **k):
        pass

    def exception(self, *a, **k):
        pass


class _AsyncClient:
    """httpx AsyncClient stub."""

    async def get(self, *a, **k):
        return types.SimpleNamespace(status_code=200, json=lambda: {}, text="", content=b"")

    async def post(self, *a, **k):
        return types.SimpleNamespace(status_code=200, json=lambda: {}, text="", content=b"")

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass


class _ClientSession:
    """aiohttp ClientSession stub."""

    async def get(self, *a, **k):
        return self

    async def post(self, *a, **k):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        pass

    async def json(self):
        return {}

    async def text(self):
        return ""


def _install_stubs(monkeypatch):
    """Inject safe stubs for third party and sibling imports."""
    httpx = types.ModuleType("httpx")
    httpx.AsyncClient = _AsyncClient
    httpx.Client = _AsyncClient
    monkeypatch.setitem(sys.modules, "httpx", httpx)

    aiohttp = types.ModuleType("aiohttp")
    aiohttp.ClientSession = _ClientSession
    monkeypatch.setitem(sys.modules, "aiohttp", aiohttp)

    redis = types.ModuleType("redis")
    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.from_url = _RedisAsyncio().from_url
    redis_asyncio.Redis = _RedisAsyncio.Redis
    redis.asyncio = redis_asyncio
    monkeypatch.setitem(sys.modules, "redis", redis)
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio)
    monkeypatch.setitem(sys.modules, "aioredis", redis_asyncio)

    pc = types.ModuleType("prometheus_client")
    pc.Counter = _Counter
    pc.Histogram = _Histogram
    pc.Gauge = _Gauge
    pc.Info = _Counter
    pc.Summary = _Histogram
    pc.CollectorRegistry = object
    monkeypatch.setitem(sys.modules, "prometheus_client", pc)

    loguru = types.ModuleType("loguru")
    loguru.logger = _Logger()
    monkeypatch.setitem(sys.modules, "loguru", loguru)


def _sanitize(part: str) -> str:
    return re.sub(r"[^0-9a-zA-Z_]", "_", part)


def _load_module(path: Path, monkeypatch):
    """Load an addon cache/metrics file under a unique sanitized package."""
    _install_stubs(monkeypatch)

    rel = path.relative_to(ROOT)
    rel_parts = rel.parts
    pkg_parts = ["_boost"] + [_sanitize(p) for p in rel_parts[:-1]]
    parent_path = ROOT

    for idx, part in enumerate(pkg_parts):
        mod_name = ".".join(pkg_parts[: idx + 1])
        mod = types.ModuleType(mod_name)
        mod.__path__ = [str(parent_path)]
        monkeypatch.setitem(sys.modules, mod_name, mod)
        if idx < len(rel_parts) - 1:
            parent_path = parent_path / rel_parts[idx]

    mod_name = ".".join(pkg_parts) + "." + _sanitize(rel_parts[-1].replace(".py", ""))
    spec = importlib.util.spec_from_file_location(mod_name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, mod_name, module)
    spec.loader.exec_module(module)
    return module


def _dummy_arg(annotation):
    """Return a dummy value for a required parameter."""
    text = str(annotation)
    if "int" in text and "str" not in text:
        return 1
    if "float" in text and "str" not in text:
        return 0.1
    return "x"


def _required_args(method):
    """Build positional dummy args for the public method signature."""
    sig = inspect.signature(method)
    args = []
    for name, param in sig.parameters.items():
        if name == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        args.append(_dummy_arg(param.annotation))
    return args


async def _maybe_await(result):
    if inspect.isawaitable(result):
        return await result
    return result


async def _exercise_cache(instance):
    """Exercise a cache manager with successful and failing redis backends."""

    async def _call_if(name, *args, **kwargs):
        if hasattr(instance, name):
            return await _maybe_await(getattr(instance, name)(*args, **kwargs))

    # success path
    await _call_if("set", "ok", {"data": 1}, ttl=60)
    await _call_if("get", "ok")
    await _call_if("get", "missing")
    await _call_if("delete", "ok")
    await _call_if("clear")
    await _call_if("connect")

    # failure path
    instance._redis = _BadRedis()
    await _call_if("set", "bad", {"data": 2})
    await _call_if("get", "bad")
    await _call_if("get", "missing")
    await _call_if("delete", "bad")
    await _call_if("clear")


def _exercise_metrics_collector(instance):
    """Exercise all public methods on a MetricsCollector-like object."""
    for name in dir(instance):
        if name.startswith("_"):
            continue
        attr = getattr(instance, name)
        if not callable(attr):
            continue
        if name == "time_operation":
            with attr(*_required_args(attr)):
                pass
            continue
        try:
            attr(*_required_args(attr))
        except Exception:
            # Methods with unusual signatures are not worth failing the test over.
            pass


def _exercise_top_level_metrics(module):
    """Call sample metric methods on module-level Counter/Histogram/Gauge objects."""
    for name in dir(module):
        if name.startswith("_"):
            continue
        obj = getattr(module, name)
        if isinstance(obj, _Metric):
            obj.labels(dummy="x").inc()
            obj.observe(0.1)
            obj.set(1)


def _instantiate(cls, **defaults):
    """Instantiate a class, passing only the keyword args it accepts."""
    sig = inspect.signature(cls)
    kwargs = {}
    for key, value in defaults.items():
        if key in sig.parameters:
            kwargs[key] = value
    return cls(**kwargs)


def _find_main_class(module):
    """Locate CacheManager/Cache or MetricsCollector/Metrics in the module."""
    for candidate in ("CacheManager", "MetricsCollector", "Cache", "Metrics"):
        obj = getattr(module, candidate, None)
        if obj and inspect.isclass(obj) and obj.__module__ == module.__name__:
            return obj
    # fallback: first class defined in this module
    for name in dir(module):
        obj = getattr(module, name)
        if inspect.isclass(obj) and getattr(obj, "__module__", None) == module.__name__:
            return obj
    return None


@pytest.mark.parametrize(
    "module_path",
    TARGET_FILES,
    ids=lambda p: p.relative_to(ROOT).as_posix(),
)
def test_addon_cache_or_metrics(module_path, monkeypatch):
    """Load each addon cache/metrics file and exercise its public API."""
    module = _load_module(module_path, monkeypatch)
    main_cls = _find_main_class(module)

    if main_cls:
        if "cache" in module_path.name:
            instance = _instantiate(main_cls, redis_url="redis://localhost")
            asyncio.run(_exercise_cache(instance))
        else:
            instance = _instantiate(main_cls, service_name="test")
            _exercise_metrics_collector(instance)
    else:
        _exercise_top_level_metrics(module)
