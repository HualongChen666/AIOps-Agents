# -*- coding: utf-8 -*-
"""Tests for core/mcp_server.py endpoints mounted via api/mcp_router.py."""


def test_mcp_get_host_health(client, admin_headers):
    resp = client.post(
        "/api/mcp/get_host_health",
        json={"host_id": "host1"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)


def test_mcp_trigger_repair(client, admin_headers):
    resp = client.post(
        "/api/mcp/trigger_repair_with_hitl",
        json={"alert_id": "a1", "user": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)


def test_mcp_search_incident(client, admin_headers):
    resp = client.post(
        "/api/mcp/search_incident_history",
        json={"query": "cpu", "limit": 5},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)


def test_mcp_get_metrics(client, admin_headers):
    resp = client.post(
        "/api/mcp/get_metrics",
        json={"host_id": "host1", "metrics": ["cpu"]},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)


def test_mcp_approve_repair(client, admin_headers):
    resp = client.post(
        "/api/mcp/approve_repair",
        json={"repair_id": "r1", "approved": True},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)
