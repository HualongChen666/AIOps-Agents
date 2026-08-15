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


@pytest.fixture(scope="session", autouse=True)
def _ensure_optional_modules():
    """Session-scoped autouse fixture that ensures optional modules are shimmed."""
    _ensure_optional_modules_in_sys_modules()


@pytest.fixture(autouse=True)
def _no_prometheus_duplicates(monkeypatch):
    """Disable Prometheus metric registration to avoid duplicate name errors."""
    import prometheus_client

    monkeypatch.setattr(prometheus_client.REGISTRY, "register", lambda *a, **k: None)
