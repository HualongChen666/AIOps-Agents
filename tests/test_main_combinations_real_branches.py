# -*- coding: utf-8 -*-
"""Real branch-coverage tests for main.py under individual addon flag permutations.

Each test gets a fresh `main.app` by setting `os.environ`, reloading `config`,
and reloading `main`.  It then uses `TestClient(main.app)` with a real admin
token to confirm that the expected routers are mounted (or not mounted) for
that environment.
"""

import importlib
import os

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

BASE_SAFETY = {
    "ENABLE_ADDONS": "true",
    "AIOPS_DISABLE_SECURITY_SCAN": "1",
    "CONFIG_VALIDATION_ENABLED": "false",
    "LOKI_ENABLED": "false",
    "TEMPO_ENABLED": "false",
    "VICTORIAMETRICS_ENABLED": "false",
    "RATE_LIMITING_ENABLED": "false",
}

MOUNTED_OK = {200, 403, 405, 422, 500}
_ADMIN = {"username": "admin", "password": "admin123"}


def _fresh_app(env_overrides):
    """Build a fresh `main.app` under the requested environment."""
    env = {**BASE_SAFETY, **{flag: "false" for flag in ALL_PACK_FLAGS}, **env_overrides}
    for key, value in env.items():
        os.environ[key] = value

    import config

    importlib.reload(config)
    import main

    importlib.reload(main)
    return main.app


def _client(env_overrides):
    app = _fresh_app(env_overrides)
    return TestClient(app, raise_server_exceptions=False)


def _admin_headers(client):
    resp = client.post("/api/v1/auth/login", json=_ADMIN)
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# (name, flag, expected-mounted endpoint, endpoint that should stay 404)
_INDIVIDUAL_CASES = [
    ("llm", "LLM_ROUTER_ENABLED", "/api/v1/ai-advanced/knowledge", "/api/v1/rag/search"),
    ("rag", "RAG_ENABLED", "/api/v1/rag/search", "/api/v1/ai-advanced/knowledge"),
    ("metrics", "METRICS_ENABLED", "/api/v1/metrics/summary", "/api/v1/topologies/types"),
    ("topology", "TOPOLOGY_ENABLED", "/api/v1/topologies/types", "/api/v1/metrics/summary"),
    ("tracing", "TRACING_ENABLED", "/api/tracing/traces", "/api/v1/logs/search"),
    ("log_aggregation", "LOG_AGGREGATION_ENABLED", "/api/v1/logs/search", "/api/tracing/traces"),
    ("workflow", "WORKFLOW_ENABLED", "/api/v1/workflows/definitions", "/api/notify/status"),
    (
        "incident",
        "INCIDENT_RESPONSE_ENABLED",
        "/api/notify/status",
        "/api/v1/workflows/definitions",
    ),
    (
        "integrations",
        "INTEGRATIONS_ENABLED",
        "/api/v1/integration/list",
        "/api/v1/enterprise/summary",
    ),
    (
        "security",
        "SECURITY_SCANNING_ENABLED",
        "/api/v1/enterprise/summary",
        "/api/v1/integration/list",
    ),
    ("plugins", "PLUGINS_ENABLED", "/api/plugins/", "/api/v1/backup/list"),
    ("mcp", "MCP_ENABLED", "/api/mcp/get_host_health", "/api/i18n/locales"),
    ("i18n", "I18N_ENABLED", "/api/i18n/locales", "/api/mcp/get_host_health"),
    ("doc", "DOC_GENERATION_ENABLED", "/api/documentation/documents", "/api/i18n/locales"),
    ("graphql", "GRAPHQL_ENABLED", "/graphql", "/api/documentation/documents"),
]


@pytest.mark.parametrize("name, flag, expected, unexpected", _INDIVIDUAL_CASES)
def test_individual_pack_enabled(name, flag, expected, unexpected):
    """ENABLE_ADDONS=true with one pack flag on; all others off."""
    with _client({flag: "true"}) as client:
        assert client.get("/health").status_code == 200

        headers = _admin_headers(client)

        mounted = client.get(expected, headers=headers)
        assert (
            mounted.status_code in MOUNTED_OK
        ), f"{name}: {expected} should be mounted (got {mounted.status_code})"

        not_mounted = client.get(unexpected, headers=headers)
        assert (
            not_mounted.status_code == 404
        ), f"{name}: {unexpected} should not be mounted (got {not_mounted.status_code})"


@pytest.mark.parametrize("flag_name", ["AIOSIGNAL_ENABLED", "OBSERVABILITY_ENABLED"])
def test_unmapped_flags_no_addon_routers(flag_name):
    """AIOSIGNAL_ENABLED / OBSERVABILITY_ENABLED are not wired into main.py,
    so turning them on with all real pack flags off should mount nothing.
    """
    with _client({flag_name: "true"}) as client:
        assert client.get("/health").status_code == 200
        headers = _admin_headers(client)
        assert client.get("/api/v1/rag/search", headers=headers).status_code == 404


def test_observability_disabled_others_enabled():
    """ENABLE_ADDONS=true, observability packs (metrics/topology/tracing/logs) off,
    all other pack flags on.  Observability routers should be absent; the rest present.
    """
    env_overrides = {
        "METRICS_ENABLED": "false",
        "TOPOLOGY_ENABLED": "false",
        "TRACING_ENABLED": "false",
        "LOG_AGGREGATION_ENABLED": "false",
    }
    for flag in ALL_PACK_FLAGS:
        if flag not in env_overrides:
            env_overrides[flag] = "true"

    with _client(env_overrides) as client:
        assert client.get("/health").status_code == 200
        headers = _admin_headers(client)

        expected_mounted = [
            "/api/v1/ai-advanced/knowledge",
            "/api/v1/rag/search",
            "/api/plugins/",
            "/api/i18n/locales",
            "/api/documentation/documents",
            "/graphql",
            "/api/v1/workflows/definitions",
            "/api/v1/integration/list",
            "/api/notify/status",
            "/api/v1/enterprise/summary",
            "/api/mcp/get_host_health",
        ]
        for path in expected_mounted:
            r = client.get(path, headers=headers)
            assert r.status_code in MOUNTED_OK, f"should be mounted: {path} (got {r.status_code})"

        expected_missing = [
            "/api/v1/metrics/summary",
            "/api/v1/topologies/types",
            "/api/tracing/traces",
            "/api/v1/logs/search",
        ]
        for path in expected_missing:
            r = client.get(path, headers=headers)
            assert r.status_code == 404, f"should not be mounted: {path} (got {r.status_code})"
