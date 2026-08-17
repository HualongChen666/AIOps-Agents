# -*- coding: utf-8 -*-
"""Parametrized coverage tests for every extensions/addons/**/lock.py."""

import asyncio  # noqa: F401  # Imported for test setup
import importlib.util
import inspect
import re
import sys  # noqa: F401  # Imported for test setup
import types
from pathlib import Path

import pytest  # noqa: F401  # Imported for test setup

ROOT = Path(__file__).resolve().parents[2]
LOCK_FILES = sorted((ROOT / "extensions" / "addons").rglob("lock.py"))


class _DummyLogger:
    def __getattr__(self, name):
        return lambda *a, **k: None


class _RedisClient:
    """Redis client mock that stores/returns the token used by the lock."""

    def __init__(self):
        self._store = {}

    async def set(self, key, value, **kwargs):
        self._store[key] = value
        return True

    async def get(self, key):
        return self._store.get(key)

    async def delete(self, key):
        self._store.pop(key, None)


class _DummyCache:
    """Cache backend for IdempotencyManager."""

    def __init__(self):
        self._memory = {}

    async def get(self, key):
        return self._memory.get(key)

    async def set(self, key, value, ttl=300):
        self._memory[key] = value

    async def delete(self, key):
        self._memory.pop(key, None)


async def _no_sleep(*args, **kwargs):
    return None


def _register_stubs(parent_dir, package_name, monkeypatch):
    """Stub optional dependencies and sibling modules for lock.py."""
    loguru_mod = types.ModuleType("loguru")
    loguru_mod.logger = _DummyLogger()
    monkeypatch.setitem(sys.modules, "loguru", loguru_mod)

    monkeypatch.setitem(sys.modules, "httpx", types.ModuleType("httpx"))
    monkeypatch.setitem(sys.modules, "aiohttp", types.ModuleType("aiohttp"))

    redis_pkg = sys.modules.get("redis") or types.ModuleType("redis")
    redis_pkg.__path__ = getattr(redis_pkg, "__path__", [])
    monkeypatch.setitem(sys.modules, "redis", redis_pkg)

    redis_asyncio = types.ModuleType("redis.asyncio")
    redis_asyncio.from_url = lambda *a, **k: _RedisClient()
    monkeypatch.setitem(sys.modules, "redis.asyncio", redis_asyncio)

    parent_pkg = types.ModuleType(package_name)
    parent_pkg.__path__ = [str(parent_dir)]
    monkeypatch.setitem(sys.modules, package_name, parent_pkg)

    settings = types.SimpleNamespace(
        service_name="test-service",
        redis_url="redis://dummy",
        enable_distributed_lock=True,
        lock_ttl_seconds=30,
        idempotency_ttl_seconds=3600,
    )
    config_mod = types.ModuleType(f"{package_name}.config")
    config_mod.settings = settings
    monkeypatch.setitem(sys.modules, f"{package_name}.config", config_mod)

    cache_mod = types.ModuleType(f"{package_name}.cache")
    cache_mod.CacheManager = _DummyCache
    monkeypatch.setitem(sys.modules, f"{package_name}.cache", cache_mod)

    return settings, redis_asyncio


@pytest.mark.parametrize("lock_path", LOCK_FILES)
def test_lock_module(lock_path, monkeypatch):
    """Load each lock.py under a synthetic package and exercise its main classes."""
    monkeypatch.setattr(asyncio, "sleep", _no_sleep)

    parent_dir = lock_path.parent
    group = re.sub(r"\W", "_", parent_dir.parent.name)
    service = re.sub(r"\W", "_", parent_dir.name)
    package_name = f"_low_lock_{group}_{service}"
    module_name = f"{package_name}.lock"

    settings, redis_asyncio = _register_stubs(parent_dir, package_name, monkeypatch)

    spec = importlib.util.spec_from_file_location(module_name, str(lock_path))
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, module_name, module)
    module.__package__ = package_name
    spec.loader.exec_module(module)

    if hasattr(module, "aioredis"):
        module.aioredis = redis_asyncio

    async def _exercise():
        # Lock/Distributed lock managers
        for cls_name in ("LockManager", "DistributedLock"):
            cls = getattr(module, cls_name, None)
            if cls is None:
                continue

            # Distributed Redis-backed lock path
            settings.enable_distributed_lock = True
            lock = cls(redis_url="redis://dummy")
            async with lock.acquire("resource", "req-1"):
                pass

            # In-process asyncio.Lock fallback path
            settings.enable_distributed_lock = False
            lock2 = cls(redis_url="redis://dummy")
            async with lock2.acquire("resource"):
                pass

            # Optional named methods if the class exposes them
            for method_name in ("release", "is_locked"):
                if not hasattr(lock, method_name):
                    continue
                method = getattr(lock, method_name)
                if not callable(method):
                    continue
                if inspect.iscoroutinefunction(method):
                    await method("resource")
                else:
                    method("resource")

            if hasattr(lock, "__enter__"):
                lock.__enter__()
            if hasattr(lock, "__exit__"):
                lock.__exit__(None, None, None)

        # Idempotency managers
        for cls_name in ("IdempotencyManager",):
            cls = getattr(module, cls_name, None)
            if cls is None:
                continue

            dummy_cache = _DummyCache()
            mgr = cls(cache=dummy_cache)

            class _Request:
                def model_dump(self):
                    return {"config": {"idempotency_key": "explicit"}}

            assert mgr.get_key(_Request(), "op") == "op:explicit"
            assert mgr.get_key({"config": {"idempotency_key": ""}}, "op")

            assert await mgr.is_processed("rid") is False
            await mgr.mark_processed("rid", result="ok")
            assert await mgr.is_processed("rid") is True

    asyncio.run(_exercise())
