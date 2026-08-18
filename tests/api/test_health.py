import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Real end-to-end tests for the health endpoints."""

from unittest.mock import patch  # noqa: E401


def test_health_liveness(client):
    """The liveness probe must return 200."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "timestamp" in data


def test_health_ping_with_auth(client, admin_headers):
    """The ping endpoint returns alive for an authorized request."""
    resp = client.get("/api/v1/health/ping", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "alive"


def test_health_ping_without_auth_remote(client):
    """The ping endpoint returns 401 for remote access without Bearer token."""
    # Test with invalid token format (not starting with "Bearer ")
    resp = client.get("/api/v1/health/ping", headers={"Authorization": "InvalidToken"})
    assert resp.status_code == 401
    data = resp.json()
    # Check nested error structure
    error_msg = data.get("error", {}).get("message", "")
    assert "Remote access requires Bearer token" in error_msg


def test_health_ping_without_token(client):
    """The ping endpoint returns 401 for remote access without any token."""
    # Test with no Authorization header
    resp = client.get("/api/v1/health/ping")
    # TestClient uses testserver which is not in ALLOWED_LOCAL_IPS by default
    # So it should require auth
    assert resp.status_code == 401


def test_health_ping_with_valid_bearer_token(client):
    """Test ping endpoint with valid Bearer token format (covers line 44 false branch)."""
    # Test with valid Bearer token format (even if token is invalid, format is correct)
    resp = client.get("/api/v1/health/ping", headers={"Authorization": "Bearer some-token"})
    # Should return 200 for local access (testserver is in ALLOWED_LOCAL_IPS)
    assert resp.status_code == 200


# def test_health_ping_no_client_info():
#     """Test ping endpoint when request.client is None (covers line 40 else branch)."""
#     from unittest.mock import MagicMock
#     import asyncio
#     from api.health_router import ping
#     from fastapi import Request
#
#     # Create a mock request with no client info
#     mock_request = MagicMock(spec=Request)
#     mock_request.client = None
#     mock_request.headers.get.return_value = ""
#
#     # Call the endpoint directly
#     result = asyncio.run(ping(mock_request))
#     assert result["status"] == "alive"
#     assert result["client"] == "unknown"


def test_health_ping_local_ip_bypass(client):
    """Test ping endpoint bypasses auth for local IPs (covers line 42->47)."""
    # The testserver is added to ALLOWED_LOCAL_IPS in conftest.py
    # This test verifies that local IPs can access without auth
    # We need to mock the request to use a local IP
    from unittest.mock import MagicMock
    import asyncio
    
    # Import the router to test directly
    from api.health_router import ping
    from fastapi import Request
    
    # Create a mock request with local IP
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "127.0.0.1"
    mock_request.headers.get.return_value = ""
    
    # Call the endpoint directly (it's async)
    result = asyncio.run(ping(mock_request))
    assert result["status"] == "alive"
    assert "timestamp" in result


@pytest.mark.smoke
def test_ready_endpoint_responds(client, admin_headers):
    """The readiness endpoint returns either 200 or 503 depending on deps."""
    resp = client.get("/ready", headers=admin_headers)
    assert resp.status_code in (200, 503)


def test_ready_endpoint_exception_handling(client):
    """Test ready endpoint returns 503 when health check fails (covers lines 159-161)."""
    with patch("api.health_router.get_readiness_status") as mock_ready:
        mock_ready.side_effect = Exception("Simulated health check failure")
        resp = client.get("/ready")
        assert resp.status_code == 503
        data = resp.json()
        error_msg = data.get("error", {}).get("message", "")
        assert "Readiness check service unavailable" in error_msg


@pytest.mark.smoke
def test_detailed_health_endpoint_responds(client, admin_headers):
    """Detailed health returns either 200 (all healthy) or 503 (some failing)."""
    resp = client.get("/api/v1/health/detailed", headers=admin_headers)
    assert resp.status_code in (200, 503)


def test_detailed_health_local_access(client):
    """Test detailed health endpoint works for local access without auth."""
    resp = client.get("/api/v1/health/detailed")
    # Local access should work (200 or 503 depending on actual health)
    assert resp.status_code in (200, 503)


def test_detailed_health_local_ip_bypass(client):
    """Test detailed health bypasses auth for local IPs (covers line 233)."""
    from unittest.mock import MagicMock
    import asyncio
    from api.health_router import detailed_health
    from fastapi import Request
    
    # Create a mock request with local IP
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "127.0.0.1"
    
    # Call the endpoint directly (it's async)
    result = asyncio.run(detailed_health(mock_request))
    # Should return health data without auth
    assert isinstance(result, dict)


def test_detailed_health_no_client_info():
    """Test detailed health when request.client is None (covers line 230 else branch)."""
    from unittest.mock import MagicMock
    import asyncio
    from api.health_router import detailed_health
    from fastapi import Request
    
    # Create a mock request with no client info
    mock_request = MagicMock(spec=Request)
    mock_request.client = None
    
    # Call the endpoint directly (it's async)
    result = asyncio.run(detailed_health(mock_request))
    # Should return health data
    assert isinstance(result, dict)


def test_detailed_health_exception_handling(client):
    """Test detailed health endpoint returns 503 on exception (covers lines 238-240)."""
    with patch("api.health_router.get_detailed_health") as mock_detailed:
        mock_detailed.side_effect = Exception("Simulated detailed health check failure")
        resp = client.get("/api/v1/health/detailed")
        assert resp.status_code == 503
        data = resp.json()
        error_msg = data.get("error", {}).get("message", "")
        assert "Detailed health check service unavailable" in error_msg


def test_trigger_health_check_with_auth(client, admin_headers):
    """Test trigger health check endpoint with authentication."""
    resp = client.post("/api/v1/health/check", headers=admin_headers)
    # Should return 200 or 503 depending on actual health
    assert resp.status_code in (200, 503)


def test_trigger_health_check_local_access(client):
    """Test trigger health check endpoint works for local access without auth."""
    resp = client.post("/api/v1/health/check")
    # Local access should work (200 or 503 depending on actual health)
    assert resp.status_code in (200, 503)


def test_trigger_health_check_local_ip_bypass(client):
    """Test trigger health check bypasses auth for local IPs (covers line 304)."""
    import asyncio
    from unittest.mock import MagicMock, AsyncMock
    from api.health_router import trigger_health_check
    from fastapi import Request
    
    # Create a mock request with local IP
    mock_request = MagicMock(spec=Request)
    mock_request.client.host = "127.0.0.1"
    
    # Mock perform_health_checks to return a valid result
    with patch("api.health_router.perform_health_checks", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {
            "status": "healthy",
            "timestamp": "2026-08-18T00:00:00Z",
            "checks": {}
        }
        
        # Call the endpoint directly
        result = asyncio.run(trigger_health_check(mock_request))
        # Should return health data without auth
        assert isinstance(result, dict)
        assert result["status"] == "healthy"


def test_trigger_health_check_no_client_info():
    """Test trigger health check when request.client is None (covers line 301 else branch)."""
    import asyncio
    from unittest.mock import MagicMock, AsyncMock
    from api.health_router import trigger_health_check
    from fastapi import Request
    
    # Create a mock request with no client info
    mock_request = MagicMock(spec=Request)
    mock_request.client = None
    
    # Mock perform_health_checks to return a valid result
    with patch("api.health_router.perform_health_checks", new_callable=AsyncMock) as mock_health:
        mock_health.return_value = {
            "status": "healthy",
            "timestamp": "2026-08-18T00:00:00Z",
            "checks": {}
        }
        
        # Call the endpoint directly
        result = asyncio.run(trigger_health_check(mock_request))
        # Should return health data
        assert isinstance(result, dict)


def test_trigger_health_check_exception_handling(client):
    """Test trigger health check returns 503 on exception (covers lines 309-311)."""
    with patch("api.health_router.perform_health_checks") as mock_health:
        mock_health.side_effect = Exception("Simulated health check trigger failure")
        resp = client.post("/api/v1/health/check")
        assert resp.status_code == 503
        data = resp.json()
        error_msg = data.get("error", {}).get("message", "")
        assert "Health check trigger service unavailable" in error_msg


def test_liveness_exception_handling(client):
    """Test liveness endpoint returns 503 on exception."""
    with patch("api.health_router.get_liveness_status") as mock_liveness:
        mock_liveness.side_effect = Exception("Simulated liveness check failure")
        resp = client.get("/health")
        assert resp.status_code == 503
        data = resp.json()
        error_msg = data.get("error", {}).get("message", "")
        assert "Health check service unavailable" in error_msg
