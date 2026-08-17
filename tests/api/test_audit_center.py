import pytest

# -*- coding: utf-8 -*-
"""Tests for api/audit_center_router.py."""

import api.audit_center_router as acr


def test_audit_center_page(client, admin_headers, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "audit_center.html").write_text("<html></html>")
    monkeypatch.setattr(acr, "BASE_DIR", tmp_path)
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


@pytest.mark.smoke
def test_audit_center_page_status(client, admin_headers):
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code in (200, 404)
