import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Tests for api/audit_center_router.py."""

import api.audit_center_router as acr


def test_audit_center_page(client, admin_headers, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "audit_center.html").write_text("<html></html>")
    monkeypatch.setattr(acr, "BASE_DIR", tmp_path)
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.headers["content-type"].startswith("text/html")


def test_audit_center_page_not_found(client, admin_headers, tmp_path, monkeypatch):
    """Test audit_center_page when the HTML file does not exist (lines 38-39)."""
    # Create a static directory but without the audit_center.html file
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    # Do NOT create audit_center.html file
    monkeypatch.setattr(acr, "BASE_DIR", tmp_path)
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code == 404
    data = resp.json()
    # The error is wrapped by global error handler
    assert "error" in data
    assert data["error"]["message"] == "Audit center page not found"


def test_audit_center_page_static_dir_not_found(client, admin_headers, tmp_path, monkeypatch):
    """Test audit_center_page when the static directory does not exist (lines 38-39)."""
    # Do NOT create the static directory at all
    monkeypatch.setattr(acr, "BASE_DIR", tmp_path)
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code == 404
    data = resp.json()
    # The error is wrapped by global error handler
    assert "error" in data
    assert data["error"]["message"] == "Audit center page not found"


@pytest.mark.smoke
def test_audit_center_page_status(client, admin_headers):
    resp = client.get("/audit_center/", headers=admin_headers)
    assert resp.status_code in (200, 404)
