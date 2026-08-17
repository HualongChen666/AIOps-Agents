# -*- coding: utf-8 -*-
"""Real tests for the gateway module.

These tests exercise the real service registry and microservice gateway client.
No external services are assumed; remote branches are exercised with a fake
HTTP client that simulates the services/ FastAPI endpoints.
"""

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest  # noqa: F401  # Imported for test setup

import gateway.services_client as services_client
from gateway import service_registry
from gateway.services_client import (
    _close_http_client,
    _get_http_client,
    _is_remote,
    _remote_call,
    approve_and_execute,
    process_alert,
    remote_datadog_query,
    remote_elk_search,
    remote_grafana_query,
    remote_incident_list,
    remote_llm_route,
    remote_rag_query,
    remote_topology,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_remote_client(responses):
    """Return a fake httpx.AsyncClient that returns canned responses.

    ``responses`` is a dict mapping a URL path suffix to a dict with:
    - ``status`` (default 200)
    - ``json`` (default None)

    Matching is done by exact URL suffix (longest key first) to avoid
    collisions such as ``/search`` also matching ``/search-query``.

    If a URL is not matched, httpx.ConnectError is raised.
    If status >= 400, httpx.HTTPStatusError is raised by the response.
    """

    class _Resp:
        def __init__(self, status, json_data, request_url, method):
            self.status_code = status
            self._json = json_data
            self.request = httpx.Request(method, request_url)

        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError(
                    "Server error",
                    request=self.request,
                    response=self,
                )

        def json(self):
            return self._json

    def _match(url, method):
        for key, val in sorted(responses.items(), key=lambda kv: len(kv[0]), reverse=True):
            if url.rstrip("/").endswith(key.rstrip("/")):
                status = val.get("status", 200)
                data = val.get("json")
                return _Resp(status, data, url, method)
        raise httpx.ConnectError("unreachable")

    async def _get(url, **kwargs):
        return _match(url, "GET")

    async def _post(url, json=None, timeout=None, **kwargs):
        return _match(url, "POST")

    client = MagicMock()
    client.get = _get
    client.post = _post
    client.is_closed = False
    return client


@pytest.fixture
def remote_client(monkeypatch):
    """Patch _get_http_client to return a fake remote HTTP client."""
    responses = {
        "/process": {"json": {"processed": True}},
        "/repairs/t1/approve": {"json": {"approved": True}},
        "/repairs": {"json": {"task_id": "t1"}},
        "/search": {"json": {"results": [{"id": "remote"}]}},
        "/route": {"json": {"content": "remote"}},
        "/nodes": {"json": {"nodes": [{"id": "n1"}]}},
        "/edges": {"json": {"edges": [{"source": "a", "target": "b"}]}},
        "/incident-response/list_methods": {"json": {"methods": ["m1"]}},
        "/datadog-integration/query-metrics": {"json": {"metrics": []}},
        "/grafana-integration/query-data": {"json": {"dashboards": []}},
        "/elk-stack/search-query": {"json": {"hits": []}},
    }
    fake = _make_remote_client(responses)
    monkeypatch.setattr(services_client, "_get_http_client", lambda: fake)
    return fake


# ---------------------------------------------------------------------------
# service_registry
# ---------------------------------------------------------------------------
def test_default_service_registry_cold_snapshot():
    """AddOnServiceRegistry.list_services returns cold data without network I/O."""
    registry = service_registry.AddOnServiceRegistry()
    services = registry.list_services()
    assert len(services) > 0
    first = services[0]
    assert first.url_env.endswith("_SERVICE_URL")
    assert first.url.startswith("http://")
    assert first.healthy is False
    assert "not performed" in (first.error or "")


def test_is_healthy_before_check():
    """is_healthy returns False before any health check has been cached."""
    registry = service_registry.AddOnServiceRegistry()
    assert registry.is_healthy("RAG_SERVICE_URL") is False


@pytest.mark.asyncio
async def test_check_all_marks_unreachable_services_unhealthy():
    """check_all pings all add-on services and caches unhealthy statuses.

    No real add-on services are expected to be running, so every service
    should be reported as unhealthy.
    """
    registry = service_registry.AddOnServiceRegistry()
    results = await registry.check_all()
    assert len(results) > 0
    assert all(not r.healthy for r in results)
    assert all(r.error for r in results)
    assert registry.is_healthy("RAG_SERVICE_URL") is False


# ---------------------------------------------------------------------------
# services_client - basic helpers
# ---------------------------------------------------------------------------
def test_default_microservice_mode_is_local():
    """_is_remote returns False when MICROSERVICE_MODE defaults to local."""
    assert _is_remote() is False


def test_is_remote_when_microservice_mode_remote(monkeypatch):
    """_is_remote returns True when MICROSERVICE_MODE is remote."""
    monkeypatch.setattr(services_client.config, "MICROSERVICE_MODE", "remote")
    assert _is_remote() is True


@pytest.mark.asyncio
async def test_http_client_lifecycle():
    """_get_http_client returns a usable httpx AsyncClient and _close_http_client closes it."""
    client = _get_http_client()
    assert isinstance(client, httpx.AsyncClient)
    assert not client.is_closed
    await _close_http_client()
    assert _get_http_client() is not client
    await _close_http_client()


@pytest.mark.asyncio
async def test_get_http_client_recreated_when_closed(monkeypatch):
    """_get_http_client creates a new client when the cached one is closed."""
    closed_client = MagicMock()
    closed_client.is_closed = True
    monkeypatch.setattr(services_client, "_http_client", closed_client)
    new_client = _get_http_client()
    assert isinstance(new_client, httpx.AsyncClient)
    await _close_http_client()


# ---------------------------------------------------------------------------
# _remote_call
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_remote_call_unconfigured_service_raises():
    """_remote_call raises RuntimeError when a service URL is not configured."""
    with pytest.raises(RuntimeError, match="not configured"):
        await _remote_call("UNKNOWN_SERVICE_URL", "GET", "/")


@pytest.mark.asyncio
async def test_remote_call_unsupported_method_raises():
    """_remote_call raises ValueError for unsupported HTTP methods."""
    with pytest.raises(ValueError, match="Unsupported HTTP method"):
        await _remote_call("RAG_SERVICE_URL", "PUT", "/")


@pytest.mark.asyncio
async def test_remote_call_get_success(remote_client, monkeypatch):
    """_remote_call GET returns the JSON payload from the fake remote service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    result = await _remote_call("RAG_SERVICE_URL", "GET", "/nodes")  # noqa: F841  # Variable for test verification
    assert result == {"nodes": [{"id": "n1"}]}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_call_post_success(remote_client, monkeypatch):
    """_remote_call POST returns the JSON payload from the fake remote service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    result = await _remote_call("RAG_SERVICE_URL", "POST", "/search", {"query": "cpu"})  # noqa: F841  # Variable for test verification
    assert result == {"results": [{"id": "remote"}]}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_call_http_error(remote_client, monkeypatch):
    """_remote_call propagates httpx.HTTPStatusError for non-2xx responses."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    error_client = _make_remote_client({"/bad": {"status": 500, "json": {}}})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: error_client)
    with pytest.raises(httpx.HTTPStatusError):
        await _remote_call("RAG_SERVICE_URL", "GET", "/bad")


@pytest.mark.asyncio
async def test_remote_call_network_error(monkeypatch):
    """_remote_call propagates httpx.ConnectError when the remote service is unreachable."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    with pytest.raises(httpx.ConnectError):
        await _remote_call("RAG_SERVICE_URL", "GET", "/missing")


# ---------------------------------------------------------------------------
# process_alert
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_process_alert_remote_success(remote_client, monkeypatch):
    """process_alert forwards the alert to the remote alert_service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("ALERT_SERVICE_URL", "http://alert")
    result = await process_alert({"id": "a1"})  # noqa: F841  # Variable for test verification
    assert result == {"processed": True}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_process_alert_remote_failure_then_local(remote_client, monkeypatch):
    """process_alert falls back to core.try_auto_heal when remote alert_service fails."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("ALERT_SERVICE_URL", "http://alert")
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    monkeypatch.setattr(services_client, "_AUTO_HEAL_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_try_auto_heal", AsyncMock(return_value="local"))
    result = await process_alert({"id": "a2"})  # noqa: F841  # Variable for test verification
    assert result == "local"  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_process_alert_local(monkeypatch):
    """process_alert uses core.try_auto_heal in local mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_AUTO_HEAL_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_try_auto_heal", AsyncMock(return_value="local"))
    result = await process_alert({"id": "a3"})  # noqa: F841  # Variable for test verification
    assert result == "local"  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_process_alert_local_auto_heal_unavailable(monkeypatch):
    """process_alert raises RuntimeError when local auto-heal is unavailable."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_AUTO_HEAL_AVAILABLE", False)
    monkeypatch.setattr(services_client, "_try_auto_heal", None)
    with pytest.raises(RuntimeError, match="Auto-heal engine is not available"):
        await process_alert({"id": "a4"})


# ---------------------------------------------------------------------------
# approve_and_execute
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_approve_and_execute_remote_success(remote_client, monkeypatch):
    """approve_and_execute creates and approves a remote repair task."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("REPAIR_SERVICE_URL", "http://repair")
    result = await approve_and_execute("alert-1", {"host": "h1", "metric": "cpu"})  # noqa: F841  # Variable for test verification
    assert result == {"approved": True}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_approve_and_execute_remote_missing_task_id(remote_client, monkeypatch):
    """approve_and_execute returns an error when the repair_service response lacks a task id."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("REPAIR_SERVICE_URL", "http://repair")
    no_id_client = _make_remote_client(
        {
            "/repairs": {"json": {"status": "created"}},
        }
    )
    monkeypatch.setattr(services_client, "_get_http_client", lambda: no_id_client)
    result = await approve_and_execute("alert-2", {"host": "h1"})  # noqa: F841  # Variable for test verification
    assert result["success"] is False
    assert "task_id" in result["error"]


@pytest.mark.asyncio
async def test_approve_and_execute_remote_failure_then_local(remote_client, monkeypatch):
    """approve_and_execute falls back to core.heal_graph when remote repair_service fails."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("REPAIR_SERVICE_URL", "http://repair")
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    monkeypatch.setattr(services_client, "_HEAL_GRAPH_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_run_heal", AsyncMock(return_value=_FakeHealState()))
    result = await approve_and_execute("alert-3", {"host": "h1"})  # noqa: F841  # Variable for test verification
    assert result["success"] is True


@pytest.mark.asyncio
async def test_approve_and_execute_local(monkeypatch):
    """approve_and_execute uses core.heal_graph in local mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_HEAL_GRAPH_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_run_heal", AsyncMock(return_value=_FakeHealState()))
    result = await approve_and_execute("alert-4", {"host": "h1"})  # noqa: F841  # Variable for test verification
    assert result["success"] is True


@pytest.mark.asyncio
async def test_approve_and_execute_local_heal_graph_unavailable(monkeypatch):
    """approve_and_execute raises RuntimeError when local heal graph is unavailable."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_HEAL_GRAPH_AVAILABLE", False)
    monkeypatch.setattr(services_client, "_run_heal", None)
    monkeypatch.setattr(services_client, "HealState", None)
    with pytest.raises(RuntimeError, match="Heal graph engine is not available"):
        await approve_and_execute("alert-5", {"host": "h1"})


class _FakeHealState:
    def __init__(self, **kwargs):
        self.alert = kwargs.get("alert")
        self.fix_applied = True
        self.error = None
        self.runbook = None
        self.analysis = None
        self.verification = None


# ---------------------------------------------------------------------------
# remote query functions
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_remote_rag_query_remote_success(remote_client, monkeypatch):
    """remote_rag_query uses the remote RAG service in remote mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag")
    result = await remote_rag_query("cpu high", top_k=3)  # noqa: F841  # Variable for test verification
    assert result == {"results": [{"id": "remote"}]}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_rag_query_local(monkeypatch):
    """remote_rag_query falls back to core.rag_engine.search_similar in local mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_RAG_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_rag_search", lambda query, top_k=5: [{"id": "local"}])
    result = await remote_rag_query("cpu", top_k=5)  # noqa: F841  # Variable for test verification
    assert result == [{"id": "local"}]  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_rag_query_unavailable(monkeypatch):
    """remote_rag_query raises RuntimeError when no RAG backend is available."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_RAG_AVAILABLE", False)
    monkeypatch.setattr(services_client, "_rag_search", None)
    with pytest.raises(RuntimeError, match="RAG engine is not available"):
        await remote_rag_query("cpu")


@pytest.mark.asyncio
async def test_remote_llm_route_remote_success(remote_client, monkeypatch):
    """remote_llm_route uses the remote LLM router service in remote mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("LLM_ROUTER_SERVICE_URL", "http://llm")
    result = await remote_llm_route("hello", models=["model-a"])  # noqa: F841  # Variable for test verification
    assert result == {"content": "remote"}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_llm_route_local(monkeypatch):
    """remote_llm_route falls back to the in-process LLM router."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_LLM_ROUTER_AVAILABLE", True)
    fake_router = MagicMock()
    fake_router.generate = AsyncMock(return_value={"content": "local"})
    monkeypatch.setattr(services_client, "_get_llm_router", lambda: fake_router)
    result = await remote_llm_route("hello")  # noqa: F841  # Variable for test verification
    assert result == {"content": "local"}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_llm_route_unavailable(monkeypatch):
    """remote_llm_route raises RuntimeError when no LLM router is available."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_LLM_ROUTER_AVAILABLE", False)
    monkeypatch.setattr(services_client, "_get_llm_router", None)
    with pytest.raises(RuntimeError, match="LLM router is not available"):
        await remote_llm_route("hello")


@pytest.mark.asyncio
async def test_remote_topology_remote_success(remote_client, monkeypatch):
    """remote_topology uses the remote topology service in remote mode."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("TOPOLOGY_SERVICE_URL", "http://topology")
    result = await remote_topology()  # noqa: F841  # Variable for test verification
    assert result == {  # noqa: F841  # Variable for test verification
        "nodes": [{"id": "n1"}],
        "edges": [{"source": "a", "target": "b"}],
    }


@pytest.mark.asyncio
async def test_remote_topology_local(monkeypatch):
    """remote_topology falls back to the in-process topology engine."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_TOPOLOGY_AVAILABLE", True)
    monkeypatch.setattr(
        services_client,
        "_get_full_link_topology",
        AsyncMock(return_value={"nodes": [{"id": "local"}], "edges": []}),
    )
    result = await remote_topology()  # noqa: F841  # Variable for test verification
    assert result == {"nodes": [{"id": "local"}], "edges": []}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_topology_unavailable(monkeypatch):
    """remote_topology raises RuntimeError when no topology backend is available."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: False)
    monkeypatch.setattr(services_client, "_TOPOLOGY_AVAILABLE", False)
    monkeypatch.setattr(services_client, "_get_full_link_topology", None)
    with pytest.raises(RuntimeError, match="Topology engine is not available"):
        await remote_topology()


@pytest.mark.asyncio
async def test_remote_incident_list(remote_client, monkeypatch):
    """remote_incident_list forwards to the incident response service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("INCIDENT_RESPONSE_SERVICE_URL", "http://incident")
    result = await remote_incident_list()  # noqa: F841  # Variable for test verification
    assert result == {"methods": ["m1"]}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_datadog_query(remote_client, monkeypatch):
    """remote_datadog_query forwards to the Datadog integration service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("DATADOG_INTEGRATION_SERVICE_URL", "http://datadog")
    result = await remote_datadog_query({"metric": "cpu"})  # noqa: F841  # Variable for test verification
    assert result == {"metrics": []}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_grafana_query(remote_client, monkeypatch):
    """remote_grafana_query forwards to the Grafana integration service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("GRAFANA_INTEGRATION_SERVICE_URL", "http://grafana")
    result = await remote_grafana_query({"dashboard": "ops"})  # noqa: F841  # Variable for test verification
    assert result == {"dashboards": []}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_elk_search(remote_client, monkeypatch):
    """remote_elk_search forwards to the ELK stack integration service."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("ELK_STACK_SERVICE_URL", "http://elk")
    result = await remote_elk_search({"index": "logs"})  # noqa: F841  # Variable for test verification
    assert result == {"hits": []}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_close_http_client_idempotent(monkeypatch):
    """_close_http_client is safe to call when no client is cached or it is already closed."""
    monkeypatch.setattr(services_client, "_http_client", None)
    await _close_http_client()
    closed_client = MagicMock()
    closed_client.is_closed = True
    monkeypatch.setattr(services_client, "_http_client", closed_client)
    await _close_http_client()
    assert services_client._http_client is None


@pytest.mark.asyncio
async def test_remote_rag_query_remote_failure_then_local(remote_client, monkeypatch):
    """remote_rag_query falls back to the in-process RAG engine when the remote service fails."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("RAG_SERVICE_URL", "http://rag")
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    monkeypatch.setattr(services_client, "_RAG_AVAILABLE", True)
    monkeypatch.setattr(services_client, "_rag_search", lambda query, top_k=5: [{"id": "local"}])
    result = await remote_rag_query("cpu")  # noqa: F841  # Variable for test verification
    assert result == [{"id": "local"}]  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_llm_route_remote_failure_then_local(remote_client, monkeypatch):
    """remote_llm_route falls back to the in-process LLM router when the remote service fails."""
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("LLM_ROUTER_SERVICE_URL", "http://llm")
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    monkeypatch.setattr(services_client, "_LLM_ROUTER_AVAILABLE", True)
    fake_router = MagicMock()
    fake_router.generate = AsyncMock(return_value={"content": "local"})
    monkeypatch.setattr(services_client, "_get_llm_router", lambda: fake_router)
    result = await remote_llm_route("hello")  # noqa: F841  # Variable for test verification
    assert result == {"content": "local"}  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_remote_topology_remote_failure_then_local(remote_client, monkeypatch):
    """remote_topology falls back to the in-process topology engine when the remote service fails."""  # noqa: E501  # Line too long (intentional)
    monkeypatch.setattr(services_client, "_is_remote", lambda: True)
    monkeypatch.setenv("TOPOLOGY_SERVICE_URL", "http://topology")
    failing_client = _make_remote_client({})
    monkeypatch.setattr(services_client, "_get_http_client", lambda: failing_client)
    monkeypatch.setattr(services_client, "_TOPOLOGY_AVAILABLE", True)
    monkeypatch.setattr(
        services_client,
        "_get_full_link_topology",
        AsyncMock(return_value={"nodes": [{"id": "local"}], "edges": []}),
    )
    result = await remote_topology()  # noqa: F841  # Variable for test verification
    assert result == {"nodes": [{"id": "local"}], "edges": []}  # noqa: F841  # Variable for test verification
