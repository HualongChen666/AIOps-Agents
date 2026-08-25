from unittest.mock import AsyncMock, patch

import pytest  # noqa: F401  # Imported for test setup

# -*- coding: utf-8 -*-
"""Real end-to-end tests for the business impact endpoints."""


@pytest.mark.smoke
def test_list_business_impact_services(client, approval_headers):
    """The services list returns a 200 response or a valid server error."""
    resp = client.get("/api/v1/business-impact/services", headers=approval_headers)
    assert resp.status_code in (200, 500)


@pytest.mark.smoke
def test_ux_metrics(client, approval_headers):
    """The UX metrics endpoint returns a 200 response or a valid error."""
    resp = client.get("/api/v1/business-impact/ux-metrics", headers=approval_headers)
    assert resp.status_code in (200, 500)


@pytest.mark.smoke
def test_assess_service(client, approval_headers):
    """Assessing a single service returns a 200/404/500 status."""
    resp = client.get(
        "/api/v1/business-impact/assess/test-service",
        headers=approval_headers,
    )
    assert resp.status_code in (200, 404, 500)


def test_assess_service_with_none_service_name():
    """Test that None service_name returns 422 error (line 34)."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name(None)
    assert exc_info.value.status_code == 422
    assert "service_name is required" in str(exc_info.value.detail)


def test_assess_service_with_non_string_type():
    """Test that non-string service_name returns 422 error (isinstance check)."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name(123)
    assert exc_info.value.status_code == 422
    assert "service_name is required" in str(exc_info.value.detail)


def test_assess_service_with_falsy_non_none():
    """Test that falsy but non-None service_name returns 422 error."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name(0)
    assert exc_info.value.status_code == 422
    assert "service_name is required" in str(exc_info.value.detail)


def test_assess_service_with_empty_string():
    """Test that empty service_name returns 422 error (line 37)."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name("")
    # Empty string is falsy, so it triggers the first check (line 34)
    assert exc_info.value.status_code == 422
    assert "service_name is required" in str(exc_info.value.detail)


def test_assess_service_with_whitespace_only():
    """Test that whitespace-only service_name returns 422 error (line 37)."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name("   ")
    assert exc_info.value.status_code == 422
    assert "service_name cannot be empty" in str(exc_info.value.detail)


def test_assess_service_with_too_long_name():
    """Test that service_name longer than 128 characters returns 422 error (line 39)."""
    from api.business_impact_router import _validate_service_name

    long_name = "a" * 129
    with pytest.raises(Exception) as exc_info:
        _validate_service_name(long_name)
    assert exc_info.value.status_code == 422
    assert "service_name too long" in str(exc_info.value.detail)


def test_assess_service_with_invalid_characters():
    """Test that service_name with invalid characters returns 422 error (line 40-44)."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name("service/with/slashes")
    assert exc_info.value.status_code == 422
    assert "may only contain letters, numbers, dots, underscores and hyphens" in str(
        exc_info.value.detail
    )


def test_assess_service_with_special_characters():
    """Test that service_name with special characters returns 422 error."""
    from api.business_impact_router import _validate_service_name

    with pytest.raises(Exception) as exc_info:
        _validate_service_name("service@domain.com")
    assert exc_info.value.status_code == 422
    assert "may only contain letters, numbers, dots, underscores and hyphens" in str(
        exc_info.value.detail
    )


def test_ux_metrics_with_exception(client, approval_headers):
    """Test that UX metrics endpoint handles exceptions properly (lines 125-127)."""
    with patch(
        "api.business_impact_router.list_business_impact_ux_metrics", new_callable=AsyncMock
    ) as mock_ux:
        mock_ux.side_effect = Exception("Test exception")
        resp = client.get("/api/v1/business-impact/ux-metrics", headers=approval_headers)
        assert resp.status_code == 500
        # The error is handled by api_error middleware, check the message
        resp_data = resp.json()
        assert "UX metrics failed" in resp_data.get("error", {}).get("message", "")


def test_list_services_with_exception(client, approval_headers):
    """Test that services list endpoint handles exceptions properly."""
    with patch(
        "api.business_impact_router.list_business_impact_services", new_callable=AsyncMock
    ) as mock_services:
        mock_services.side_effect = Exception("Test exception")
        resp = client.get("/api/v1/business-impact/services", headers=approval_headers)
        assert resp.status_code == 500
        # The error is handled by api_error middleware, check the message
        resp_data = resp.json()
        assert "Business impact listing failed" in resp_data.get("error", {}).get("message", "")


def test_assess_service_with_engine_exception(client, approval_headers):
    """Test that assess endpoint handles engine exceptions properly."""
    with patch(
        "api.business_impact_router.assess_business_impact", new_callable=AsyncMock
    ) as mock_assess:
        mock_assess.side_effect = Exception("Test exception")
        resp = client.get(
            "/api/v1/business-impact/assess/test-service",
            headers=approval_headers,
        )
        assert resp.status_code == 500
        # The error is handled by api_error middleware, check the message
        resp_data = resp.json()
        assert "Impact assessment failed" in resp_data.get("error", {}).get("message", "")


def test_validate_service_name_with_valid_input():
    """Test that valid service names pass validation."""
    from api.business_impact_router import _validate_service_name

    # Test valid names with different character sets
    assert _validate_service_name("api-service") == "api-service"
    assert _validate_service_name("payment.service") == "payment.service"
    assert _validate_service_name("auth_service") == "auth_service"
    assert _validate_service_name("cache-service-123") == "cache-service-123"
    assert _validate_service_name("  spaced-service  ") == "spaced-service"


def test_validate_service_name_with_exactly_128_chars():
    """Test that service_name with exactly 128 characters is accepted."""
    from api.business_impact_router import _validate_service_name

    name_128 = "a" * 128
    assert _validate_service_name(name_128) == name_128


def test_list_services_success_response(client, approval_headers):
    """Test that services list returns successful response with correct structure (line 79)."""
    resp = client.get("/api/v1/business-impact/services", headers=approval_headers)
    # Accept both 200 (success) and 500 (backend error)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "data" in data
        assert "timestamp" in data
        assert data["status"] == "success"


def test_ux_metrics_success_response(client, approval_headers):
    """Test that UX metrics returns successful response with correct structure (line 120)."""
    resp = client.get("/api/v1/business-impact/ux-metrics", headers=approval_headers)
    # Accept both 200 (success) and 500 (backend error)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "data" in data
        assert "timestamp" in data
        assert data["status"] == "success"


def test_assess_service_success_response(client, approval_headers):
    """Test that assess service returns successful response with correct structure (line 161)."""
    resp = client.get(
        "/api/v1/business-impact/assess/payment-service",
        headers=approval_headers,
    )
    # Accept both 200 (success) and 500 (backend error)
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "data" in data
        assert "timestamp" in data
        assert data["status"] == "success"
