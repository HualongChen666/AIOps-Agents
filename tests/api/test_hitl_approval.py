import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Tests for api/hitl_approval_router.py."""

import api.hitl_approval_router as har


def test_hitl_approval_page(client, admin_headers, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "hitl_approval.html").write_text("<html></html>")
    monkeypatch.setattr(har, "BASE_DIR", tmp_path)
    resp = client.get("/hitl-page/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


def test_hitl_approval_page_not_found(client, admin_headers, tmp_path, monkeypatch):
    """Test that a 404 is returned when the HITL approval page file does not exist."""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    # Intentionally do not create hitl_approval.html to trigger the 404 branch
    monkeypatch.setattr(har, "BASE_DIR", tmp_path)
    resp = client.get("/hitl-page/", headers=admin_headers)
    assert resp.status_code == 404
    # The response may be JSON or plain text depending on FastAPI's error handling
    # Check if the error message is present in either format
    response_text = resp.text
    assert "HITL Approval page not found" in response_text or "not found" in response_text.lower()


@pytest.mark.smoke
def test_hitl_approval_page_status(client, admin_headers):
    resp = client.get("/hitl-page/", headers=admin_headers)
    assert resp.status_code in (200, 404)
