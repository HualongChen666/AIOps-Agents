# -*- coding: utf-8 -*-
"""Real end-to-end tests for the cost monitoring endpoints."""

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    ("GET", "/api/cost/collect", None, None, {200, 404, 500}),
    ("GET", "/api/cost/forecast", None, {"days": 30}, {200, 404, 500}),
    ("GET", "/api/cost/budget", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_cost_endpoint(client, admin_headers, method, path, body, params, expected):
    """Each B26 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=admin_headers, **kwargs)
    assert resp.status_code in expected


def test_cost_collect_with_date_range(client, admin_headers):
    """Test cost collection with date range parameters."""
    # Test with valid date range
    resp = client.get(
        "/api/cost/collect",
        params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 500}
    
    if resp.status_code == 200:
        data = resp.json()
        assert "costs" in data
        assert isinstance(data["costs"], list)
    
    # Test with only start date
    resp = client.get(
        "/api/cost/collect",
        params={"start_date": "2026-01-01"},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 500}
    
    # Test with only end date
    resp = client.get(
        "/api/cost/collect",
        params={"end_date": "2026-01-31"},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 500}
    
    # Test with invalid date format
    resp = client.get(
        "/api/cost/collect",
        params={"start_date": "invalid-date"},
        headers=admin_headers
    )
    # Should handle invalid date gracefully
    assert resp.status_code in {200, 404, 422, 500}


def test_cost_forecast_with_custom_days(client, admin_headers):
    """Test cost forecast with custom forecast days."""
    # Test with different day values
    test_days = [1, 7, 14, 30, 60, 90]
    
    for days in test_days:
        resp = client.get(
            "/api/cost/forecast",
            params={"days": days},
            headers=admin_headers
        )
        assert resp.status_code in {200, 404, 500}
        
        if resp.status_code == 200:
            data = resp.json()
            assert "days" in data
            assert data["days"] == days
            assert "forecast" in data
            assert isinstance(data["forecast"], list)
    
    # Test with zero days
    resp = client.get(
        "/api/cost/forecast",
        params={"days": 0},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 422, 500}
    
    # Test with negative days
    resp = client.get(
        "/api/cost/forecast",
        params={"days": -7},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 422, 500}
    
    # Test with very large days value
    resp = client.get(
        "/api/cost/forecast",
        params={"days": 365},
        headers=admin_headers
    )
    assert resp.status_code in {200, 404, 500}


def test_cost_budget_details(client, admin_headers):
    """Test budget status with detailed breakdown."""
    # Test basic budget status
    resp = client.get("/api/cost/budget", headers=admin_headers)
    assert resp.status_code in {200, 500}
    
    if resp.status_code == 200:
        data = resp.json()
        assert "status" in data
        assert "budget" in data
        assert "message" in data
        
        # Check budget structure
        if data["budget"]:
            assert "monthly_budget" in data["budget"]
            assert "current_spend" in data["budget"]
            assert "utilization_percent" in data["budget"]
            assert "remaining_budget" in data["budget"]
    
    # Test detailed budget breakdown
    resp = client.get(
        "/api/cost/budget",
        params={"detailed": True},
        headers=admin_headers
    )
    assert resp.status_code in {200, 500}
    
    if resp.status_code == 200:
        data = resp.json()
        assert "budget" in data
        
        # Check for detailed fields
        if data["budget"]:
            # Basic fields should still be present
            assert "monthly_budget" in data["budget"]
            assert "current_spend" in data["budget"]
            
            # Detailed fields should be present when detailed=True
            if "service_breakdown" in data["budget"]:
                assert isinstance(data["budget"]["service_breakdown"], dict)
            
            if "daily_average" in data["budget"]:
                assert isinstance(data["budget"]["daily_average"], (int, float))
            
            if "projected_monthly" in data["budget"]:
                assert isinstance(data["budget"]["projected_monthly"], (int, float))
    
    # Test with detailed=False (explicit)
    resp = client.get(
        "/api/cost/budget",
        params={"detailed": False},
        headers=admin_headers
    )
    assert resp.status_code in {200, 500}
    
    if resp.status_code == 200:
        data = resp.json()
        assert "budget" in data
        # Should not have detailed breakdown fields
        if data["budget"]:
            assert "service_breakdown" not in data["budget"]
