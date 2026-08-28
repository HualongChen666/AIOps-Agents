# -*- coding: utf-8 -*-
"""Tests for api/batch_router.py."""


def test_batch_alerts(client, admin_headers):
    resp = client.post("/api/v1/batch/alerts", json=["nonexistent"], headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        assert "results" in data


def test_batch_metrics(client, admin_headers):
    resp = client.post("/api/v1/batch/metrics", json=["cpu"], headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        data = resp.json()
        assert "results" in data
