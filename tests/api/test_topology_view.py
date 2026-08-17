import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Tests for api/topology_view_router.py."""

import api.topology_view_router as tvr


def test_topology_view_page(client, admin_headers, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "topology.html").write_text("<html></html>")
    monkeypatch.setattr(tvr, "BASE_DIR", tmp_path)
    resp = client.get("/topology/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


@pytest.mark.smoke
def test_topology_view_page_status(client, admin_headers):
    resp = client.get("/topology/", headers=admin_headers)
    assert resp.status_code in (200, 404)
