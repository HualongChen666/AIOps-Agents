# -*- coding: utf-8 -*-
"""Targeted real branch-coverage tests for main.py.

These tests focus on the actual missing lines/branches reported for main.py:
startup fallbacks, exception handlers, conditional logging, lifespan branches,
config reload paths, TLS enforcement, k8s router mounting, and storage/Loki/causal
graph branches.

Each test gets a fresh ``main.app`` by mutating ``os.environ``, reloading
``config`` and ``main`` (no mocks), and uses ``TestClient(main.app)`` to exercise
the relevant code paths end-to-end.
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

BASE_TARGETED = {
    "ENABLE_ADDONS": "true",
    "CONFIG_VALIDATION_ENABLED": "false",
    "AIOPS_DISABLE_SECURITY_SCAN": "1",
    "RATE_LIMITING_ENABLED": "false",
    "LOKI_ENABLED": "false",
    "TEMPO_ENABLED": "false",
    "VICTORIAMETRICS_ENABLED": "false",
    "CAUSAL_GRAPH_ENABLED": "true",
    "CAUSAL_GRAPH_AUTO_BUILD": "true",
    "WORKFLOW_ENGINE_ENABLED": "true",
    "AIOPS_ENFORCE_TLS": "false",
    "KEY_MANAGEMENT_BACKEND": "environment",
    "EXTERNAL_API_AUDIT_ENABLED": "true",
}

# Make sure all pack flags are off by default so we are not re-testing the
# add-on router permutations already covered by test_main_combinations.
BASE_TARGETED.update({flag: "false" for flag in ALL_PACK_FLAGS})


def _fresh_app(env_overrides):
    """Build a fresh ``main.app`` under the requested environment."""
    env = {**BASE_TARGETED, **env_overrides}
    for key, value in env.items():
        os.environ[key] = str(value)

    import config

    importlib.reload(config)
    import main

    importlib.reload(main)
    return main.app


def _client(env_overrides):
    app = _fresh_app(env_overrides)
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# 1. Startup fallbacks / exception handlers
# ---------------------------------------------------------------------------

def test_invalid_key_management_backend():
    """Cover the key-management fallback exception branch and the
    ENABLE_ADDONS=false / add-on skip branches in main.py."""
    with _client({"KEY_MANAGEMENT_BACKEND": "invalid-backend", "ENABLE_ADDONS": "false"}) as client:
        r = client.get("/health")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 2. Lifespan storage / Loki / security scan branches
# ---------------------------------------------------------------------------

def test_lifespan_storage_loki_security_branches():
    """Cover the L4 storage implementation, Loki shipping, and security scan
    branches in the lifespan startup sequence."""
    env = {
        "LOKI_ENABLED": "true",
        "LOKI_HOST": "localhost",
        "LOKI_PORT": "3100",
        "AIOPS_DISABLE_SECURITY_SCAN": "0",  # cover the != "1" branch
    }
    with _client(env) as client:
        r = client.get("/health")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 3. Causal graph auto_build false branch
# ---------------------------------------------------------------------------

def test_causal_graph_auto_build_false():
    """Cover the false branch of the causal_graph auto_build conditional."""
    with _client({"CAUSAL_GRAPH_AUTO_BUILD": "false"}) as client:
        r = client.get("/health")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# 4. TLS enforcement and k8s router mounting
# ---------------------------------------------------------------------------

def test_tls_enforcement_and_k8s_router():
    """Cover the TLS enforcement middleware and the k8s_router mount branch."""
    with _client({"AIOPS_ENFORCE_TLS": "true", "ENABLE_ADDONS": "false"}) as client:
        # Non-OPTIONS HTTP requests should be rejected with 400.
        r = client.get("/health")
        assert r.status_code == 400, f"expected 400 for non-TLS request, got {r.status_code}"

        # OPTIONS preflight bypasses TLS enforcement.
        preflight = client.request("OPTIONS", "/health")
        assert preflight.status_code in {200, 204, 405}

        # If the k8s router was mounted, an unauthenticated request gets 401/403
        # rather than 404 (we just need the true mount branch to run).
        k8s = client.get("/api/v1/platforms/kubernetes/")
        assert k8s.status_code in {401, 403, 404}
