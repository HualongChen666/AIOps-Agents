# -*- coding: utf-8 -*-
"""Functional tests for the plugin microservice (``services.plugin_service``).

The service is exercised end-to-end through the FastAPI app against an
in-memory SQLite database, so the assertions cover the real repository,
business-logic and HTTP layers.
"""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Must be set before the settings object is imported.
os.environ["PLUGIN_SERVICE_USE_IN_MEMORY"] = "true"

from services.plugin_service.grpc.client import PluginRPCClient  # noqa: E402
from services.plugin_service.grpc.server import PluginRPCServer  # noqa: E402
from services.plugin_service.main_app import app  # noqa: E402
from services.plugin_service.saga import PluginSaga  # noqa: E402

pytestmark = pytest.mark.services


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


def _plugin_payload(name: str | None = None) -> dict:
    return {
        "name": name or f"plugin-{uuid.uuid4().hex[:8]}",
        "version": "1.0.0",
        "description": "test plugin",
        "author": "pytest",
        "plugin_type": "collector",
        "default_config": {"interval": 60},
    }


# ---------------------------------------------------------------------------
# Health / metrics / stats
# ---------------------------------------------------------------------------
def test_health_reports_ok(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "plugin-service"
    assert body["database"] == "sqlite-memory"
    assert body["uptime_seconds"] >= 0


def test_metrics_exposes_prometheus_text(client: TestClient):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "plugin_service_plugins_created_total" in response.text


def test_stats_shape(client: TestClient):
    response = client.get("/stats")
    assert response.status_code == 200
    body = response.json()
    for key in (
        "total_plugins",
        "active_plugins",
        "inactive_plugins",
        "error_plugins",
        "total_executions",
        "successful_executions",
        "failed_executions",
    ):
        assert key in body


# ---------------------------------------------------------------------------
# Plugin CRUD
# ---------------------------------------------------------------------------
def test_create_and_fetch_plugin(client: TestClient):
    payload = _plugin_payload("crud-plugin")
    created = client.post("/plugins", json=payload, params={"created_by": "tester"})
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "crud-plugin"
    assert body["status"] == "inactive"
    assert body["created_by"] == "tester"

    fetched = client.get(f"/plugins/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    by_name = client.get("/plugins/by-name/crud-plugin")
    assert by_name.status_code == 200
    assert by_name.json()["id"] == body["id"]


def test_create_plugin_rejects_empty_name(client: TestClient):
    payload = _plugin_payload()
    payload["name"] = "   "
    response = client.post("/plugins", json=payload)
    assert response.status_code == 422


def test_list_plugins_reports_total_and_filters(client: TestClient):
    for _ in range(2):
        client.post("/plugins", json=_plugin_payload())

    listed = client.get("/plugins", params={"limit": 1})
    assert listed.status_code == 200
    body = listed.json()
    assert len(body["plugins"]) == 1
    assert body["total"] >= 1

    bad_filter = client.get("/plugins", params={"status": "nope"})
    assert bad_filter.status_code == 422


def test_update_plugin(client: TestClient):
    plugin_id = client.post("/plugins", json=_plugin_payload()).json()["id"]

    response = client.put(f"/plugins/{plugin_id}", json={"description": "updated"})
    assert response.status_code == 200
    assert response.json()["description"] == "updated"

    assert client.put("/plugins/does-not-exist", json={"description": "x"}).status_code == 404


def test_delete_plugin(client: TestClient):
    plugin_id = client.post("/plugins", json=_plugin_payload()).json()["id"]

    assert client.delete(f"/plugins/{plugin_id}").status_code == 200
    assert client.get(f"/plugins/{plugin_id}").status_code == 404
    assert client.delete(f"/plugins/{plugin_id}").status_code == 404


def test_get_unknown_plugin_returns_404(client: TestClient):
    assert client.get("/plugins/unknown-id").status_code == 404
    assert client.get("/plugins/by-name/unknown").status_code == 404


# ---------------------------------------------------------------------------
# Executions
# ---------------------------------------------------------------------------
def test_create_and_fetch_execution(client: TestClient):
    plugin_id = client.post("/plugins", json=_plugin_payload()).json()["id"]

    created = client.post(
        "/executions",
        json={
            "plugin_id": plugin_id,
            "plugin_name": "whatever",
            "execution_type": "collect",
            "trigger_type": "manual",
        },
        params={"executed_by": "tester"},
    )
    assert created.status_code == 201
    execution_id = created.json()["id"]

    fetched = client.get(f"/executions/{execution_id}")
    assert fetched.status_code == 200
    assert fetched.json()["success"] is False

    listed = client.get("/executions", params={"plugin_id": plugin_id})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1
    assert client.get("/executions/missing").status_code == 404


def test_run_unknown_plugin_returns_404(client: TestClient):
    response = client.post("/plugins/never-registered/run", json={"input_data": {}})
    assert response.status_code == 404


def test_run_plugin_without_collect_method_records_failure(client: TestClient):
    """A registered DB plugin that is not present in the plugin manager fails cleanly."""
    name = f"not-loaded-{uuid.uuid4().hex[:6]}"
    client.post("/plugins", json=_plugin_payload(name))

    response = client.post(f"/plugins/{name}/run", json={"input_data": {}})
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["error_message"]


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
def test_config_crud(client: TestClient):
    plugin_id = client.post("/plugins", json=_plugin_payload()).json()["id"]

    created = client.post(
        "/configs",
        json={"plugin_id": plugin_id, "plugin_name": "cfg", "config_data": {"a": 1}},
    )
    assert created.status_code == 201
    config = created.json()
    assert config["config_version"] == 1

    by_plugin = client.get(f"/configs/by-plugin/{plugin_id}")
    assert by_plugin.status_code == 200
    assert by_plugin.json()["config_data"] == {"a": 1}

    updated = client.put(f"/configs/{config['id']}", json={"config_data": {"a": 2}})
    assert updated.status_code == 200
    assert updated.json()["config_version"] == 2

    assert client.delete(f"/configs/{config['id']}").status_code == 200
    assert client.get(f"/configs/{config['id']}").status_code == 404
    assert client.delete(f"/configs/{config['id']}").status_code == 404


def test_config_lookup_missing(client: TestClient):
    assert client.get("/configs/nope").status_code == 404
    assert client.get("/configs/by-plugin/nope").status_code == 404


# ---------------------------------------------------------------------------
# Saga
# ---------------------------------------------------------------------------
def test_registration_saga_creates_plugin_and_config(client: TestClient):
    name = f"saga-ok-{uuid.uuid4().hex[:6]}"
    response = client.post("/sagas/plugin-registration", json=_plugin_payload(name))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"

    plugin = client.get(f"/plugins/by-name/{name}")
    assert plugin.status_code == 200
    config = client.get(f"/configs/by-plugin/{plugin.json()['id']}")
    assert config.status_code == 200
    assert config.json()["config_data"] == {"interval": 60}


def test_registration_saga_compensates_on_failure(client: TestClient, monkeypatch):
    name = f"saga-fail-{uuid.uuid4().hex[:6]}"

    def boom(self, *args, **kwargs):
        raise RuntimeError("config store unavailable")

    monkeypatch.setattr(
        "services.plugin_service.main_app.PluginService.create_config", boom
    )

    response = client.post("/sagas/plugin-registration", json=_plugin_payload(name))
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "compensated"
    assert "config store unavailable" in body["error"]
    # The plugin created by the first step must have been rolled back.
    assert client.get(f"/plugins/by-name/{name}").status_code == 404


# ---------------------------------------------------------------------------
# RPC surface
# ---------------------------------------------------------------------------
def test_rpc_list_and_dispatch(client: TestClient):
    assert client.get("/rpc").json() == {"methods": []}

    server = PluginRPCServer()

    async def echo(value: str = "") -> str:
        return f"echo:{value}"

    server.register("echo", echo)

    import asyncio

    assert asyncio.run(server.call("echo", value="hi")) == "echo:hi"
    assert server.list_methods() == ["echo"]

    with pytest.raises(ValueError):
        asyncio.run(server.call("missing"))


def test_rpc_client_roundtrip_in_process():
    import asyncio

    server = PluginRPCServer()

    async def ping() -> str:
        return "pong"

    server.register("ping", ping)
    client = PluginRPCClient(server=server)
    assert asyncio.run(client.call("ping")) == {"method": "ping", "result": "pong"}


def test_rpc_client_requires_target():
    with pytest.raises(ValueError):
        PluginRPCClient()


def test_rpc_endpoint_unknown_method(client: TestClient):
    assert client.post("/rpc/nope", json={}).status_code == 404


# ---------------------------------------------------------------------------
# Saga primitive
# ---------------------------------------------------------------------------
def test_saga_runs_steps_in_order():
    import asyncio

    seen: list[str] = []

    async def first():
        seen.append("first")
        return 1

    async def second():
        seen.append("second")
        return 2

    saga = PluginSaga(saga_id="s1")
    saga.add_step("first", first).add_step("second", second)
    asyncio.run(saga.execute())

    assert seen == ["first", "second"]
    assert saga.status == "success"
    assert saga.results == {"first": 1, "second": 2}
