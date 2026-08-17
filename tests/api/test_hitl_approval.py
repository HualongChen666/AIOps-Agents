import pytest

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


@pytest.mark.smoke
def test_hitl_approval_page_status(client, admin_headers):
    resp = client.get("/hitl-page/", headers=admin_headers)
    assert resp.status_code in (200, 404)
