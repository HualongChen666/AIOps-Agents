import pytest  # noqa: F401  # Imported for test setup

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


def test_rag_history_page_file_not_found(client, admin_headers, tmp_path, monkeypatch):
    """测试文件不存在时返回 404 错误"""
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    # 不创建 rag_history_search.html 文件
    monkeypatch.setattr(rhr, "BASE_DIR", tmp_path)
    resp = client.get("/rag_history/", headers=admin_headers)
    assert resp.status_code == 404
    # 检查响应内容包含错误信息
    resp_text = resp.text
    assert "RAG 历史搜索页面未部署" in resp_text or "NOT_FOUND" in resp_text


def test_rag_history_page_static_dir_not_found(client, admin_headers, tmp_path, monkeypatch):
    """测试 static 目录不存在时返回 404 错误"""
    # 不创建 static 目录
    monkeypatch.setattr(rhr, "BASE_DIR", tmp_path)
    resp = client.get("/rag_history/", headers=admin_headers)
    assert resp.status_code == 404
    # 检查响应内容包含错误信息
    resp_text = resp.text
    assert "RAG 历史搜索页面未部署" in resp_text or "NOT_FOUND" in resp_text


@pytest.mark.smoke
def test_rag_history_page_status(client, admin_headers):
    resp = client.get("/rag_history/", headers=admin_headers)
    assert resp.status_code in (200, 404)
