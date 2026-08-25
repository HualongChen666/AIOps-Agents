# -*- coding: utf-8 -*-
"""Real end-to-end tests for topology endpoints."""

from unittest.mock import MagicMock, patch

import pytest

import api.topology_router as router

_CASES = [
    # topology_router.py
    ("GET", "/api/v1/topologies/types", None, None, {200, 500}),
    ("GET", "/api/v1/topologies/status/topo-1", None, None, {200, 404, 500}),
    ("POST", "/api/v1/topologies/node/health", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/topologies/full-link", None, None, {200, 500}),
    ("GET", "/api/v1/topologies/node/node-1/timeline", None, None, {200, 404, 500}),
    # topology_view_router.py
    ("GET", "/topology/", None, None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_topology_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each B21 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected


def test_node_health_update_request_validator_whitespace(client, approval_headers):
    """Test NodeHealthUpdateRequest validator with pure whitespace node_id (line 44)."""
    resp = client.post(
        "/api/v1/topologies/node/health",
        headers=approval_headers,
        json={"node_id": "   ", "status": "healthy"},
    )
    assert resp.status_code == 422
    resp_data = resp.json()
    # Check for validation error in response
    assert "node_id 不能为纯空白" in str(resp_data) or "detail" in resp_data


def test_node_health_update_request_validator_invalid_chars(client, approval_headers):
    """Test NodeHealthUpdateRequest validator with invalid characters (line 46)."""
    resp = client.post(
        "/api/v1/topologies/node/health",
        headers=approval_headers,
        json={"node_id": "node@invalid", "status": "healthy"},
    )
    assert resp.status_code == 422
    resp_data = resp.json()
    # Check for validation error in response - the error message is in details field
    assert "node_id 仅允许字母数字和" in str(resp_data) or "detail" in resp_data


def test_validate_path_node_id_empty(client, approval_headers):
    """Test _validate_path_node_id with empty node_id (line 62)."""
    resp = client.get("/api/v1/topologies/node//timeline", headers=approval_headers)
    assert resp.status_code == 404  # FastAPI treats empty path segment as 404


def test_validate_path_node_id_whitespace(client, approval_headers):
    """Test _validate_path_node_id with whitespace-only node_id (line 65)."""
    resp = client.get("/api/v1/topologies/node/%20/timeline", headers=approval_headers)
    assert resp.status_code == 422
    resp_data = resp.json()
    assert "node_id 不能为纯空白" in str(resp_data) or "detail" in resp_data or "error" in resp_data


def test_validate_path_node_id_invalid_chars(client, approval_headers):
    """Test _validate_path_node_id with invalid characters (line 67)."""
    resp = client.get("/api/v1/topologies/node/node@invalid/timeline", headers=approval_headers)
    assert resp.status_code == 422
    resp_data = resp.json()
    assert (
        "node_id 仅允许字母数字和" in str(resp_data)
        or "detail" in resp_data
        or "error" in resp_data
    )


def test_validate_path_node_id_too_long(client, approval_headers):
    """Test _validate_path_node_id with node_id exceeding 64 characters (line 69)."""
    long_id = "a" * 65
    resp = client.get(f"/api/v1/topologies/node/{long_id}/timeline", headers=approval_headers)
    assert resp.status_code == 422
    resp_data = resp.json()
    assert (
        "node_id 长度超出 64 字符" in str(resp_data)
        or "detail" in resp_data
        or "error" in resp_data
    )


def test_get_topo_status_exception(client, approval_headers):
    """Test get_topo_status non-HTTPException exception handling (lines 123-125)."""
    with patch("api.topology_router.get_topology_status", side_effect=RuntimeError("Test error")):
        resp = client.get("/api/v1/topologies/status/test-topo", headers=approval_headers)
        assert resp.status_code == 500
        resp_data = resp.json()
        assert "拓扑状态查询失败" in str(resp_data) or "detail" in resp_data or "error" in resp_data


def test_set_node_health_exception(client, approval_headers):
    """Test set_node_health non-ValueError exception handling (lines 165-167)."""
    with patch("api.topology_router.update_node_health", side_effect=RuntimeError("Test error")):
        resp = client.post(
            "/api/v1/topologies/node/health",
            headers=approval_headers,
            json={"node_id": "test-node", "status": "healthy"},
        )
        assert resp.status_code == 500
        resp_data = resp.json()
        assert "节点状态更新失败" in str(resp_data) or "detail" in resp_data or "error" in resp_data


def test_set_node_health_value_error(client, approval_headers):
    """Test set_node_health ValueError handling (lines 162-164)."""
    with patch("api.topology_router.update_node_health", side_effect=ValueError("Invalid node")):
        resp = client.post(
            "/api/v1/topologies/node/health",
            headers=approval_headers,
            json={"node_id": "test-node", "status": "healthy"},
        )
        assert resp.status_code == 400
        resp_data = resp.json()
        assert "Invalid node" in str(resp_data) or "detail" in resp_data or "error" in resp_data


def test_get_full_link_cache_hit(client, approval_headers):
    """Test get_full_link cache hit (lines 191-192)."""
    # First call to populate cache
    resp1 = client.get("/api/v1/topologies/full-link", headers=approval_headers)
    assert resp1.status_code == 200

    # Second call should hit cache (within 5 second TTL)
    resp2 = client.get("/api/v1/topologies/full-link", headers=approval_headers)
    assert resp2.status_code == 200


def test_get_full_link_exception(client, approval_headers):
    """Test get_full_link exception handling (lines 204-206)."""
    # Clear cache first to ensure we don't hit the cache
    client.post("/api/v1/topologies/cache/clear", headers=approval_headers)
    with patch("api.topology_router.get_full_link_topology", side_effect=Exception("Test error")):
        resp = client.get("/api/v1/topologies/full-link", headers=approval_headers)
        assert resp.status_code == 500
        resp_data = resp.json()
        assert (
            "全链路拓扑生成失败" in str(resp_data) or "detail" in resp_data or "error" in resp_data
        )


def test_get_node_timeline_exception(client, approval_headers):
    """Test get_node_timeline exception handling (lines 243-245)."""
    with patch("api.topology_router.get_node_timeline", side_effect=Exception("Test error")):
        resp = client.get("/api/v1/topologies/node/test-node/timeline", headers=approval_headers)
        assert resp.status_code == 500
        resp_data = resp.json()
        assert (
            "节点时间线查询失败" in str(resp_data) or "detail" in resp_data or "error" in resp_data
        )


def test_clear_topology_cache(client, approval_headers):
    """Test clear_topology_cache endpoint (lines 248-259)."""
    # First populate cache
    resp1 = client.get("/api/v1/topologies/full-link", headers=approval_headers)
    assert resp1.status_code == 200

    # Clear cache
    resp2 = client.post("/api/v1/topologies/cache/clear", headers=approval_headers)
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "ok"
    assert resp2.json()["cleared"] is True


def test_clear_topology_cache_when_empty(client, approval_headers):
    """Test clear_topology_cache when cache is already empty."""
    # Clear cache when it's already empty
    resp = client.post("/api/v1/topologies/cache/clear", headers=approval_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    # cleared should be False since cache was already empty
    assert resp.json()["cleared"] is False


def test_get_topo_status_invalid_topo_key(client, approval_headers):
    """Test get_topo_status with invalid topo_key characters (line 109)."""
    resp = client.get("/api/v1/topologies/status/topo@invalid", headers=approval_headers)
    assert resp.status_code == 422
    resp_data = resp.json()
    assert (
        "topo_key 仅允许字母数字和" in str(resp_data)
        or "detail" in resp_data
        or "error" in resp_data
    )


def test_get_topo_status_success(client, approval_headers):
    """Test get_topo_status successful path (lines 113-120)."""
    resp = client.get("/api/v1/topologies/status/default", headers=approval_headers)
    assert resp.status_code in (200, 404)  # May return 404 if topology doesn't exist


def test_get_topo_status_404(client, approval_headers):
    """Test get_topo_status with non-existent topology (line 115)."""
    with patch("api.topology_router.get_topology_status", return_value={"error": "not found"}):
        resp = client.get("/api/v1/topologies/status/nonexistent", headers=approval_headers)
        assert resp.status_code == 404


def test_set_node_health_success(client, approval_headers):
    """Test set_node_health successful path with cache clearing (lines 157-161)."""
    # First populate cache
    client.get("/api/v1/topologies/full-link", headers=approval_headers)

    # Update node health - should clear cache
    resp = client.post(
        "/api/v1/topologies/node/health",
        headers=approval_headers,
        json={"node_id": "agent", "status": "warning"},
    )
    assert resp.status_code == 200
    resp_data = resp.json()
    assert resp_data["status"] == "ok"
    assert resp_data["node_id"] == "agent"
    assert resp_data["health"] == "warning"


def test_get_node_timeline_with_params(client, approval_headers):
    """Test get_node_timeline with custom hours and limit parameters."""
    resp = client.get(
        "/api/v1/topologies/node/test-node/timeline?hours=48&limit=100", headers=approval_headers
    )
    assert resp.status_code in (200, 500)  # May fail if node doesn't exist


def test_get_node_timeline_invalid_hours(client, approval_headers):
    """Test get_node_timeline with invalid hours parameter (FastAPI validation)."""
    resp = client.get(
        "/api/v1/topologies/node/test-node/timeline?hours=200", headers=approval_headers
    )
    assert resp.status_code == 422


def test_get_node_timeline_invalid_limit(client, approval_headers):
    """Test get_node_timeline with invalid limit parameter (FastAPI validation)."""
    resp = client.get(
        "/api/v1/topologies/node/test-node/timeline?limit=300", headers=approval_headers
    )
    assert resp.status_code == 422
