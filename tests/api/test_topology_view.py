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


def test_topology_view_page_file_not_found(client, admin_headers, tmp_path, monkeypatch):
    """测试拓扑页面文件不存在时的404错误响应。"""
    # 创建一个临时目录但不创建 topology.html 文件
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    monkeypatch.setattr(tvr, "BASE_DIR", tmp_path)
    resp = client.get("/topology/", headers=admin_headers)
    assert resp.status_code == 404
    # 检查响应中包含错误信息
    resp_data = resp.json()
    # 自定义错误格式
    assert resp_data["success"] is False
    assert resp_data["error"]["code"] == "NOT_FOUND"
    assert resp_data["error"]["message"] == "Topology page not found"


@pytest.mark.smoke
def test_topology_view_page_status(client, admin_headers):
    resp = client.get("/topology/", headers=admin_headers)
    assert resp.status_code in (200, 404)
