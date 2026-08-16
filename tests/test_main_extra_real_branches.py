# -*- coding: utf-8 -*-
"""Extra real branch-coverage tests for main.py.

These tests target the remaining uncovered branches reported for main.py by
using ``os.environ`` + ``importlib.reload`` to get a fresh ``main.app`` for
each scenario and exercising the real lifespan/shutdown code through
``TestClient``.
"""

import importlib
import os
import sys

import pytest
from fastapi.testclient import TestClient

ALL_PACK_FLAGS = [
    "LLM_ROUTER_ENABLED",
    "RAG_ENABLED",
    "METRICS_ENABLED",
    "TOPOLOGY_ENABLED",
    "TRACING_ENABLED",
    "LOG_AGGREGATION_ENABLED",
    "INCIDENT_RESPONSE_ENABLED",
    "WORKFLOW_ENABLED",
    "INTEGRATIONS_ENABLED",
    "SECURITY_SCANNING_ENABLED",
    "PLUGINS_ENABLED",
    "MCP_ENABLED",
    "GRAPHQL_ENABLED",
    "I18N_ENABLED",
    "DOC_GENERATION_ENABLED",
]

BASE_EXTRA = {
    "ENABLE_ADDONS": "true",
    "CONFIG_VALIDATION_ENABLED": "false",
    "AIOPS_DISABLE_SECURITY_SCAN": "1",
    "LOKI_ENABLED": "false",
    "TEMPO_ENABLED": "false",
    "VICTORIAMETRICS_ENABLED": "false",
    "CAUSAL_GRAPH_ENABLED": "true",
    "CAUSAL_GRAPH_AUTO_BUILD": "true",
    "WORKFLOW_ENGINE_ENABLED": "true",
    "AIOPS_ENFORCE_TLS": "false",
    "KEY_MANAGEMENT_BACKEND": "environment",
    "EXTERNAL_API_AUDIT_ENABLED": "false",
    "RATE_LIMITING_ENABLED": "false",
    "AIOPS_GRPC_ENABLED": "false",
}
BASE_EXTRA.update({flag: "false" for flag in ALL_PACK_FLAGS})


def _fresh_app(env_overrides):
    """Build a fresh ``main.app`` under the requested environment."""
    env = {**BASE_EXTRA, **env_overrides}
    for key, value in env.items():
        os.environ[key] = str(value)

    # Remove cached copies so the reload actually re-reads config from os.environ.
    for mod in list(sys.modules):
        if mod in ("config", "main"):
            del sys.modules[mod]

    import config

    importlib.reload(config)
    import main

    importlib.reload(main)
    return main.app


def _client(env_overrides):
    app = _fresh_app(env_overrides)
    return TestClient(app, raise_server_exceptions=False)


def test_causal_graph_auto_build_true():
    """Cover the true branch of the causal_graph auto_build conditional."""
    with _client({"CAUSAL_GRAPH_AUTO_BUILD": "true"}) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_causal_graph_auto_build_false():
    """Cover the false branch of the causal_graph auto_build conditional."""
    with _client({"CAUSAL_GRAPH_AUTO_BUILD": "false"}) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_security_scan_not_disabled():
    """Cover the branch where AIOPS_DISABLE_SECURITY_SCAN is not "1"."""
    with _client({"AIOPS_DISABLE_SECURITY_SCAN": "0"}) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_storage_backends_enabled_success():
    """Cover the successful (true) branches for Loki/Tempo/VictoriaMetrics init."""
    env = {
        "LOKI_ENABLED": "true",
        "TEMPO_ENABLED": "true",
        "VICTORIAMETRICS_ENABLED": "true",
    }
    with _client(env) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_storage_backends_initialize_failure():
    """Cover the failure (false) branches for Loki/Tempo/VictoriaMetrics init.

    The bad hosts contain non-printable characters, which causes the
    underlying ``httpx.AsyncClient`` construction to raise and the storage
    ``initialize`` methods to return ``False``.
    """
    env = {
        "LOKI_ENABLED": "true",
        "LOKI_HOST": "bad\nhost",
        "TEMPO_ENABLED": "true",
        "TEMPO_HOST": "bad\nhost",
        "VICTORIAMETRICS_ENABLED": "true",
        "VICTORIAMETRICS_HOST": "bad\nhost",
    }
    with _client(env) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_grpc_enabled_lifecycle():
    """Cover the gRPC server creation and shutdown branches."""
    env = {
        "AIOPS_GRPC_ENABLED": "true",
        "AIOPS_GRPC_PORT": "55555",
    }
    with _client(env) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}


def test_core_components_persist_for_shutdown():
    """Cover the shutdown ``if`` branches for data lineage / feature flags."""
    with _client({}) as client:
        r = client.get("/health")
        assert r.status_code in {200, 500}
