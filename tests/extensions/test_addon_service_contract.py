# -*- coding: utf-8 -*-
"""Regression tests for the addon microservice service contract.

Every addon ``main_app.py`` template expects its ``service.py`` to expose the
same runtime surface (``_state`` + async lifecycle endpoints + per-operation
handlers + ``call``).  Before ``ServiceStateContract`` was introduced these
wrappers raised ``AttributeError`` / ``TypeError`` at request time, so every
endpoint of these microservices answered HTTP 500.

These tests exercise the *real* FastAPI apps end to end (no mocks of the
contract itself).
"""

from __future__ import annotations

import importlib

import pytest
from starlette.testclient import TestClient

# Addon microservices whose service.py lacked the contract (previously 500 on
# every endpoint).  Grouped by the engine family they belong to.
BROKEN_APPS = [
    # docs/policy engine family
    "extensions.addons.infrastructure.api_standards_service.main_app",
    "extensions.addons.infrastructure.data_standards_service.main_app",
    "extensions.addons.infrastructure.plugin_market_service.main_app",
    "extensions.addons.infrastructure.plugin_system_service.main_app",
    "extensions.addons.documentation.sphinx_documentation_service.main_app",
    # infra executor family
    "extensions.addons.infrastructure.ansible_automation_service.main_app",
    "extensions.addons.infrastructure.automated_deployment_service.main_app",
    "extensions.addons.infrastructure.automated_ops_service.main_app",
    "extensions.addons.infrastructure.backup_recovery_drill_service.main_app",
    "extensions.addons.infrastructure.chaos_mesh_service.main_app",
    "extensions.addons.infrastructure.kubernetes_orchestration_service.main_app",
    "extensions.addons.infrastructure.pgbackrest_backup_service.main_app",
    "extensions.addons.infrastructure.service_mesh_service.main_app",
    "extensions.addons.infrastructure.terraform_iac_service.main_app",
    "extensions.addons.infrastructure.velero_backup_service.main_app",
    # security scanner family
    "extensions.addons.infrastructure.fastapi_security_service.main_app",
    "extensions.addons.infrastructure.open_source_license_service.main_app",
    "extensions.addons.security.penetration_testing_service.main_app",
    "extensions.addons.security.security_audit_service.main_app",
    "extensions.addons.security.security_scanning_service.main_app",
    "extensions.addons.security.sqlalchemy_security_service.main_app",
    # operations engine family
    "extensions.addons.operations.capacity_planning_service.main_app",
    "extensions.addons.operations.incident_runbook_service.main_app",
    "extensions.addons.operations.workflow_engine_service.main_app",
    # connector bus family
    "extensions.addons.integrations.elk_stack_service.main_app",
    "extensions.addons.integrations.github_repository_service.main_app",
    "extensions.addons.integrations.kafka_event_service.main_app",
    "extensions.addons.integrations.message_queue_service.main_app",
]

# Services whose endpoints are gated by the gateway auth middleware.
AUTH_GATED = {
    "extensions.addons.infrastructure.config_service.main_app",
    "extensions.addons.infrastructure.user_service.main_app",
}


def _client(module_name: str) -> TestClient:
    module = importlib.import_module(module_name)
    return TestClient(module.app, raise_server_exceptions=False)


@pytest.mark.parametrize("module_name", BROKEN_APPS)
def test_lifecycle_endpoints_no_longer_500(module_name):
    client = _client(module_name)
    assert client.get("/health").status_code == 200
    assert client.get("/stats").status_code == 200
    assert client.post("/rpc/list_methods").status_code == 200
    assert client.post("/rpc/stats").status_code == 200


@pytest.mark.parametrize("module_name", sorted(AUTH_GATED))
def test_auth_gated_services_return_401_not_500(module_name):
    client = _client(module_name)
    assert client.get("/health").status_code == 200
    assert client.get("/stats").status_code == 401
    assert client.post("/rpc/list_methods").status_code == 401


@pytest.mark.parametrize("module_name", BROKEN_APPS)
def test_rpc_list_methods_returns_operations(module_name):
    module = importlib.import_module(module_name)
    client = TestClient(module.app, raise_server_exceptions=False)
    body = client.post("/rpc/list_methods").json()
    assert "base_methods" not in body  # sanity: it is a list of names
    assert "list_methods" in body
    assert set(module.OPERATIONS).issubset(set(body))


CONTRACT = "extensions.addons.engines.service_contract"


def test_service_state_contract_unit():
    """The shared contract exposes the documented surface on a tiny subclass."""
    contract = importlib.import_module(CONTRACT)

    class Dummy(contract.ServiceStateContract):
        OPERATIONS = ["do_thing"]

        @staticmethod
        def execute_operation(name, params):
            return {"feature": name, "success": True, "status": "ok", "result": {"echo": params}}

    service = Dummy(metrics=None, cache=None)
    import asyncio

    assert asyncio.run(service.list_methods())["result"]["methods"] == [
        "do_thing",
        "get_state",
        "backup_state",
        "restore_state",
        "get_stats",
        "list_methods",
    ]
    asyncio.run(service.backup_state({"name": "snap"}))
    assert asyncio.run(service.restore_state({"name": "snap"}))["result"]["restored"] is True
    assert asyncio.run(service.get_stats())["result"]["feature_count"] == 1
    # per-operation handler via __getattr__
    handler = service.do_thing
    assert asyncio.run(handler({"config": {"x": 1}}))["result"]["echo"] == {"x": 1}


def test_security_feature_dispatch_normalises_list_result():
    """Security scanners return lists; the FeatureResponse model needs a dict."""
    module = importlib.import_module("extensions.addons.security.security_audit_service.main_app")
    client = TestClient(module.app, raise_server_exceptions=False)
    resp = client.post(f"/{module.URL_PREFIX}/run-zap-scan", json={"config": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["result"], dict)
