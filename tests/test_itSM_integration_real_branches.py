# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core/integration/l7/itSM_integration.py.

These tests drive the real ``ITSMIntegration`` with a real local HTTP server,
real in-memory configuration payloads and no network mocks.
"""

import asyncio
import json
import socket
import threading
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from core.integration.l7.itSM_integration import (
    ITSMIntegration,
    get_itsm_integration,
    init_itsm_integration,
)

# In-memory store shared by the test HTTP server.
_STORE = {"incidents": {}, "issues": {}, "inc_counter": 0, "issue_counter": 0}
_STORE_LOCK = threading.Lock()


def _reset_store():
    """Reset the in-memory server store for clean test runs."""
    with _STORE_LOCK:
        _STORE["incidents"].clear()
        _STORE["issues"].clear()
        _STORE["inc_counter"] = 0
        _STORE["issue_counter"] = 0


class _ITSMServerHandler(BaseHTTPRequestHandler):
    """Tiny HTTP server that returns ServiceNow/Jira shaped responses."""

    def log_message(self, fmt, *args):  # noqa: D401
        pass

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        return {}

    def _send_json(self, body, status=200):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _parse_path(self):
        parsed = urllib.parse.urlparse(self.path)
        return parsed, urllib.parse.parse_qs(parsed.query)

    def do_POST(self):  # noqa: N802
        parsed, _ = self._parse_path()
        if parsed.path == "/api/now/table/incident":
            data = self._read_json()
            with _STORE_LOCK:
                _STORE["inc_counter"] += 1
                number = f"INC{_STORE['inc_counter']:04d}"
            sys_id = f"sys-{number.lower()}"
            incident = {
                "number": number,
                "sys_id": sys_id,
                "short_description": data.get("short_description", ""),
                "description": data.get("description", ""),
                "state": "New",
                "sys_created_on": "2024-01-01T00:00:00Z",
            }
            with _STORE_LOCK:
                _STORE["incidents"][number] = incident
                _STORE["incidents"][sys_id] = incident
            self._send_json({"result": incident})
        elif parsed.path == "/rest/api/2/issue":
            data = self._read_json()
            with _STORE_LOCK:
                _STORE["issue_counter"] += 1
                key = f"PROJ-{_STORE['issue_counter']}"
            issue = {
                "key": key,
                "id": str(10000 + _STORE["issue_counter"]),
                "fields": data.get("fields", {}),
            }
            with _STORE_LOCK:
                _STORE["issues"][key] = issue
            self._send_json({"key": key, "id": issue["id"]})
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):  # noqa: N802
        parsed, qs = self._parse_path()
        if parsed.path == "/api/now/table/incident":
            query = qs.get("sysparm_query", [""])[0]
            number = query.split("number=", 1)[1] if "number=" in query else None
            with _STORE_LOCK:
                incident = _STORE["incidents"].get(number) if number else None
            if incident:
                self._send_json({"result": [incident]})
            else:
                self._send_json({"result": []})
        else:
            self.send_response(404)
            self.end_headers()

    def do_PATCH(self):  # noqa: N802
        parsed, _ = self._parse_path()
        if parsed.path.startswith("/api/now/table/incident/"):
            sys_id = parsed.path.rsplit("/", 1)[1]
            data = self._read_json()
            with _STORE_LOCK:
                incident = _STORE["incidents"].get(sys_id)
                if incident:
                    incident.update(data)
                    incident["sys_updated_on"] = "2024-01-01T01:00:00Z"
                    self._send_json({"result": incident})
                    return
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):  # noqa: N802
        parsed, _ = self._parse_path()
        if parsed.path.startswith("/rest/api/2/issue/"):
            key = parsed.path.rsplit("/", 1)[1]
            data = self._read_json()
            with _STORE_LOCK:
                issue = _STORE["issues"].get(key)
                if issue:
                    issue["fields"].update(data.get("fields", {}))
                    self.send_response(204)
                    self.end_headers()
                    return
            self.send_response(404)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="module")
def itsm_server():
    """Yield a real local HTTP server URL for the test module."""
    _reset_store()
    server = HTTPServer(("127.0.0.1", 0), _ITSMServerHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


@pytest.fixture(autouse=True)
def _reset_store_fixture():
    """Reset the server store before every test."""
    _reset_store()
    yield


# ---------------------------------------------------------------------------
# Initialization and configuration
# ---------------------------------------------------------------------------
def test_init_unconfigured():
    itsm = ITSMIntegration()
    assert itsm._is_initialized is False
    assert itsm.servicenow_enabled is False
    assert itsm.jira_enabled is False
    status = itsm.get_status()
    assert status["initialized"] is False
    assert status["servicenow"]["enabled"] is False
    assert status["jira"]["enabled"] is False


def test_init_servicenow_only():
    itsm = ITSMIntegration({"servicenow": {"enabled": True, "instance": "test"}})
    assert itsm._is_initialized is True
    assert itsm.servicenow_enabled is True
    assert itsm.jira_enabled is False


def test_init_jira_only():
    itsm = ITSMIntegration({"jira": {"enabled": True, "url": "http://example"}})
    assert itsm._is_initialized is True
    assert itsm.servicenow_enabled is False
    assert itsm.jira_enabled is True


def test_init_both_enabled():
    itsm = ITSMIntegration(
        {
            "servicenow": {"enabled": True, "instance": "test"},
            "jira": {"enabled": True, "url": "http://example"},
        }
    )
    assert itsm._is_initialized is True
    assert itsm.servicenow_enabled is True
    assert itsm.jira_enabled is True


def test_authentication_config_loaded():
    itsm = ITSMIntegration(
        {
            "servicenow": {
                "enabled": True,
                "instance": "test",
                "username": "svc.user",
                "password": "secret",
            },
            "jira": {
                "enabled": True,
                "url": "http://example",
                "username": "jira.user",
                "api_token": "token",
            },
        }
    )
    assert itsm.servicenow_username == "svc.user"
    assert itsm.servicenow_password == "secret"
    assert itsm.jira_username == "jira.user"
    assert itsm.jira_api_token == "token"


# ---------------------------------------------------------------------------
# ServiceNow ticket lifecycle
# ---------------------------------------------------------------------------
def test_create_servicenow_incident_success_all_severities_and_assignment(
    itsm_server,
):
    async def _run():
        base_url = f"{itsm_server}/api/now/table"
        itsm = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": base_url,
                }
            }
        )
        # severity "low" and no assignment_group (false branch)
        r1 = await itsm.create_servicenow_incident("title1", "desc1", severity="low")
        assert "error" not in r1
        assert r1["number"].startswith("INC")
        assert r1["severity"] == "low"
        assert r1["assignment_group"] is None

        # severity "medium" and assignment_group truthy branch
        r2 = await itsm.create_servicenow_incident(
            "title2",
            "desc2",
            severity="medium",
            assignment_group="network-ops",
        )
        assert r2["number"].startswith("INC")
        assert r2["severity"] == "medium"
        assert r2["assignment_group"] == "network-ops"

        # severity "high" and default priority
        r3 = await itsm.create_servicenow_incident("title3", "desc3", severity="high", priority=1)
        assert r3["severity"] == "high"
        assert r3["priority"] == 1

    asyncio.run(_run())


def test_create_servicenow_incident_disabled():
    async def _run():
        itsm = ITSMIntegration()
        result = await itsm.create_servicenow_incident("title", "desc")
        assert result == {"error": "ServiceNow not enabled"}

    asyncio.run(_run())


def test_create_servicenow_incident_connection_error():
    async def _run():
        itsm = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": "http://127.0.0.1:1/api/now/table",
                }
            }
        )
        result = await itsm.create_servicenow_incident("boom", "desc")
        assert "error" in result

    asyncio.run(_run())


def test_update_servicenow_incident_found_and_close(itsm_server):
    async def _run():
        base_url = f"{itsm_server}/api/now/table"
        itsm = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": base_url,
                }
            }
        )
        created = await itsm.create_servicenow_incident("alert", "something wrong", severity="high")
        number = created["number"]
        # close the incident via update
        updated = await itsm.update_servicenow_incident(number, {"state": "Closed"})
        assert updated["updated"] is True
        assert updated["updates"]["state"] == "Closed"
        assert updated["number"] == number

    asyncio.run(_run())


def test_update_servicenow_incident_not_found(itsm_server):
    async def _run():
        base_url = f"{itsm_server}/api/now/table"
        itsm = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": base_url,
                }
            }
        )
        result = await itsm.update_servicenow_incident("INC-UNKNOWN", {"state": "Closed"})
        assert result == {"error": "Incident not found"}

    asyncio.run(_run())


def test_update_servicenow_incident_disabled():
    async def _run():
        itsm = ITSMIntegration()
        result = await itsm.update_servicenow_incident("INC001", {"state": "Closed"})
        assert result == {"error": "ServiceNow not enabled"}

    asyncio.run(_run())


def test_update_servicenow_incident_connection_error():
    async def _run():
        itsm = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": "http://127.0.0.1:1/api/now/table",
                }
            }
        )
        result = await itsm.update_servicenow_incident("INC001", {"state": "Closed"})
        assert "error" in result

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Jira ticket lifecycle
# ---------------------------------------------------------------------------
def test_create_jira_issue_success_and_default_project(itsm_server):
    async def _run():
        itsm = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": itsm_server,
                    "username": "u",
                    "api_token": "t",
                }
            }
        )
        # explicit project_key covers first `if not project_key` false branch
        r1 = await itsm.create_jira_issue("summary1", "desc1", project_key="PROJ")
        assert "error" not in r1
        assert r1["key"].startswith("PROJ-")
        assert r1["project_key"] == "PROJ"

        # missing project_key falls back to default_project
        itsm2 = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": itsm_server,
                    "username": "u",
                    "api_token": "t",
                    "default_project": "DEFT",
                }
            }
        )
        r2 = await itsm2.create_jira_issue("summary2", "desc2")
        assert r2["project_key"] == "DEFT"

    asyncio.run(_run())


def test_create_jira_issue_missing_project():
    async def _run():
        itsm = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": "http://example",
                    "username": "u",
                    "api_token": "t",
                }
            }
        )
        result = await itsm.create_jira_issue("summary", "desc")
        assert result == {"error": "Project key is required"}

    asyncio.run(_run())


def test_create_jira_issue_disabled():
    async def _run():
        itsm = ITSMIntegration()
        result = await itsm.create_jira_issue("summary", "desc")
        assert result == {"error": "Jira not enabled"}

    asyncio.run(_run())


def test_create_jira_issue_connection_error():
    async def _run():
        itsm = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": "http://127.0.0.1:1",
                    "username": "u",
                    "api_token": "t",
                }
            }
        )
        result = await itsm.create_jira_issue("summary", "desc", project_key="PROJ")
        assert "error" in result

    asyncio.run(_run())


def test_update_jira_issue_success(itsm_server):
    async def _run():
        itsm = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": itsm_server,
                    "username": "u",
                    "api_token": "t",
                }
            }
        )
        created = await itsm.create_jira_issue("summary", "desc", project_key="PROJ")
        key = created["key"]
        updated = await itsm.update_jira_issue(key, {"summary": "updated summary"})
        assert updated["updated"] is True
        assert updated["key"] == key

    asyncio.run(_run())


def test_update_jira_issue_disabled():
    async def _run():
        itsm = ITSMIntegration()
        result = await itsm.update_jira_issue("PROJ-1", {"summary": "x"})
        assert result == {"error": "Jira not enabled"}

    asyncio.run(_run())


def test_update_jira_issue_connection_error():
    async def _run():
        itsm = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": "http://127.0.0.1:1",
                    "username": "u",
                    "api_token": "t",
                }
            }
        )
        result = await itsm.update_jira_issue("PROJ-1", {"summary": "x"})
        assert "error" in result

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Webhook / event sync branches
# ---------------------------------------------------------------------------
def test_sync_alert_to_itsm_all_targets(itsm_server):
    async def _run():
        base_url = f"{itsm_server}/api/now/table"
        itsm_both = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": base_url,
                },
                "jira": {
                    "enabled": True,
                    "url": itsm_server,
                    "username": "u",
                    "api_token": "t",
                    "default_project": "PROJ",
                },
            }
        )

        # target_system servicenow only
        r1 = await itsm_both.sync_alert_to_itsm(
            "A-1", {"description": "cpu high", "severity": "high"}, target_system="servicenow"
        )
        assert "servicenow" in r1
        assert "jira" not in r1

        # target_system jira only
        r2 = await itsm_both.sync_alert_to_itsm(
            "A-2", {"description": "disk full"}, target_system="jira"
        )
        assert "jira" in r2
        assert "servicenow" not in r2

        # target_system both
        r3 = await itsm_both.sync_alert_to_itsm("A-3", {"description": "oom"}, target_system="both")
        assert "servicenow" in r3
        assert "jira" in r3

        # unknown target_system -> empty dict
        r4 = await itsm_both.sync_alert_to_itsm(
            "A-4", {"description": "noop"}, target_system="unknown"
        )
        assert r4 == {}

        # servicenow target but servicenow disabled
        sn_disabled = ITSMIntegration(
            {
                "jira": {
                    "enabled": True,
                    "url": itsm_server,
                    "username": "u",
                    "api_token": "t",
                    "default_project": "PROJ",
                }
            }
        )
        r5 = await sn_disabled.sync_alert_to_itsm(
            "A-5", {"description": "x"}, target_system="servicenow"
        )
        assert r5 == {}

        # jira target but jira disabled
        jira_disabled = ITSMIntegration(
            {
                "servicenow": {
                    "enabled": True,
                    "instance": "test",
                    "username": "u",
                    "password": "p",
                    "base_url": base_url,
                }
            }
        )
        r6 = await jira_disabled.sync_alert_to_itsm(
            "A-6", {"description": "y"}, target_system="jira"
        )
        assert r6 == {}

        # both target but no system enabled
        none = ITSMIntegration()
        r7 = await none.sync_alert_to_itsm("A-7", {}, target_system="both")
        assert r7 == {}

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
def test_global_singleton_lifecycle():
    inst = init_itsm_integration(
        {
            "servicenow": {"enabled": True, "instance": "test"},
            "jira": {"enabled": True, "url": "http://example"},
        }
    )
    assert isinstance(inst, ITSMIntegration)
    assert get_itsm_integration() is inst
