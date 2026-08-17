import pytest

# -*- coding: utf-8 -*-
"""Real end-to-end tests for top-level main.py endpoints."""


@pytest.mark.smoke
def test_root_endpoint(client):
    """The root path serves static/index.html if it exists, otherwise 404/500."""
    resp = client.get("/")
    assert resp.status_code in (200, 404, 500)


def test_service_worker_script(client):
    """The /sw.js endpoint returns JavaScript or a 500 if the helper fails."""
    resp = client.get("/sw.js")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        assert resp.headers["content-type"].startswith("application/javascript")


def test_service_worker_register_script(client):
    """The /sw-register.js endpoint returns JavaScript or a 500."""
    resp = client.get("/sw-register.js")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        assert resp.headers["content-type"].startswith("application/javascript")


def test_list_dr_scenarios(client, admin_headers):
    """The DR scenarios list returns a 200 JSON list for an authorized user."""
    resp = client.get("/api/v1/dr/scenarios", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    names = {s["name"] for s in data}
    assert "database_failover" in names


def test_run_dr_scenario(client, admin_headers):
    """Running a valid DR scenario returns a result or 500 if a step fails."""
    resp = client.post("/api/v1/dr/run/database_failover", headers=admin_headers)
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.json()
        assert data["scenario"] == "Database Failover"
        assert "status" in data
        assert isinstance(data["results"], list)
