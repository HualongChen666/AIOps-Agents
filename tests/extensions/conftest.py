# -*- coding: utf-8 -*-
"""Shared fixtures for extension tests."""

import sys
from unittest.mock import MagicMock

import pytest

OPTIONAL_MODULES = {
    "neo4j": ["GraphDatabase", "Driver"],
    "qdrant_client": ["QdrantClient"],
    "elasticsearch": ["Elasticsearch"],
    "kafka": ["KafkaProducer", "KafkaConsumer", "KafkaAdminClient"],
    "confluent_kafka": ["Producer", "Consumer", "KafkaError"],
}


def _ensure_optional_modules_in_sys_modules():
    """Insert MagicMock modules for missing optional dependencies."""
    for name, attrs in OPTIONAL_MODULES.items():
        if name in sys.modules:
            continue
        mod = MagicMock(name=name)
        for attr in attrs:
            setattr(mod, attr, MagicMock(name=f"{name}.{attr}"))
        sys.modules[name] = mod


# Make missing optional deps available before test modules are collected.
_ensure_optional_modules_in_sys_modules()

# Import real modules that tests commonly monkeypatch, so the original objects are
# captured in the sys.modules snapshot used for cleanup between tests.
for _mod_name in (
    "fastapi",
    "starlette",
    "starlette.responses",
    "httpx",
    "redis",
    "redis.asyncio",
    "aiohttp",
    "requests",
    "uvicorn",
):
    try:
        __import__(_mod_name)
    except Exception:
        pass

# Snapshot of sys.modules after the conftest setup; used to restore shimmed
# modules between tests and prevent cross-test leakage.
_INITIAL_SYS_MODULES = dict(sys.modules)


@pytest.fixture(scope="session", autouse=True)
def _ensure_optional_modules():
    """Session-scoped autouse fixture that ensures optional modules are shimmed."""
    _ensure_optional_modules_in_sys_modules()


@pytest.fixture(autouse=True)
def _no_prometheus_duplicates(monkeypatch):
    """Disable Prometheus metric registration to avoid duplicate name errors."""
    import prometheus_client

    monkeypatch.setattr(prometheus_client.REGISTRY, "register", lambda *a, **k: None)


@pytest.fixture(autouse=True, scope="function")
def _restore_sys_modules_after_each_test():
    """Restore sys.modules entries that were shimmed during a test.

    Some low-coverage tests monkeypatch fastapi/starlette/httpx/redis/etc via
    sys.modules. This fixture makes sure those entries are restored to their
    original module objects so later tests see the real implementation again.
    """
    yield
    for name, mod in _INITIAL_SYS_MODULES.items():
        if sys.modules.get(name) is not mod:
            sys.modules[name] = mod
    # Remove synthetic package trees created by importlib.util smoke tests.
    for name in list(sys.modules):
        if name.startswith("__low_") or name.startswith("_low_") or name.startswith("services."):
            sys.modules.pop(name, None)
