import pytest
# -*- coding: utf-8 -*-
"""Tests for api/rag_history_router.py."""

import api.rag_history_router as rhr


def test_rag_history_page(client, admin_headers, tmp_path, monkeypatch):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    (static_dir / "rag_history_search.html").write_text("<html></html>")
    monkeypatch.setattr(rhr, "BASE_DIR", tmp_path)
    resp = client.get("/rag_history/", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")


@pytest.mark.smoke
def test_rag_history_page_status(client, admin_headers):
    resp = client.get("/rag_history/", headers=admin_headers)
    assert resp.status_code in (200, 404)
