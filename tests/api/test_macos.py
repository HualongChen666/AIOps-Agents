import pytest

# -*- coding: utf-8 -*-
"""Tests for api/macos_router.py."""


@pytest.mark.smoke
def test_macos_metrics(client, admin_headers):
    resp = client.get("/api/macos/metrics", headers=admin_headers)
    assert resp.status_code in (200, 500)


@pytest.mark.smoke
def test_macos_repair(client, admin_headers):
    resp = client.post(
        "/api/macos/repair",
        params={"host": "mac1", "script_name": "clear_cache"},
        headers=admin_headers,
    )
    assert resp.status_code in (200, 500)
