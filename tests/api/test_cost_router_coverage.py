# -*- coding: utf-8 -*-
"""
Test coverage for cost_router.py
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import sys

# Mock the core.cost_monitor module before importing
mock_cost_monitor = MagicMock()
sys.modules['core.cost_monitor'] = mock_cost_monitor


@pytest.fixture
def mock_cost_functions():
    """Mock cost monitoring functions"""
    return {
        'collect_costs': Mock(),
        'forecast_costs': Mock(),
        'budget_status': Mock()
    }


@pytest.fixture
def cost_app(mock_cost_functions):
    """Create test app with cost router"""
    from fastapi import FastAPI
    from api.cost_router import router as cost_router
    
    app = FastAPI()
    app.include_router(cost_router)
    
    # Set the mock functions
    mock_cost_monitor.collect_costs = mock_cost_functions['collect_costs']
    mock_cost_monitor.forecast_costs = mock_cost_functions['forecast_costs']
    mock_cost_monitor.budget_status = mock_cost_functions['budget_status']
    
    yield app


@pytest.fixture
def client(cost_app):
    """Test client"""
    return TestClient(cost_app)


class TestGetCollect:
    """Test get_collect endpoint"""
    
    def test_get_collect_success(self, client, mock_cost_functions):
        """Test successful cost data collection"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 100.0},
            {"date": "2026-07-02", "amount": 150.0},
            {"date": "2026-07-03", "amount": 120.0}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert "costs" in data
        assert len(data["costs"]) == 3
        assert data["costs"][0]["amount"] == 100.0
        mock_cost_functions['collect_costs'].assert_called_once()
    
    def test_get_collect_empty_data(self, client, mock_cost_functions):
        """Test cost collection with no data"""
        mock_cost_functions['collect_costs'].return_value = []
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 404
        assert "No cost data found" in response.json()["detail"]
    
    def test_get_collect_none_data(self, client, mock_cost_functions):
        """Test cost collection with None return"""
        mock_cost_functions['collect_costs'].return_value = None
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 404
        assert "No cost data found" in response.json()["detail"]
    
    def test_get_collect_single_record(self, client, mock_cost_functions):
        """Test cost collection with single record"""
        mock_cost_data = [{"date": "2026-07-01", "amount": 100.0}]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["costs"]) == 1
    
    def test_get_collect_large_dataset(self, client, mock_cost_functions):
        """Test cost collection with large dataset"""
        mock_cost_data = [
            {"date": f"2026-07-{i:02d}", "amount": 100.0 + i}
            for i in range(1, 32)
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["costs"]) == 31
    
    def test_get_collect_function_error(self, client, mock_cost_functions):
        """Test cost collection with function error"""
        mock_cost_functions['collect_costs'].side_effect = Exception("Collection failed")
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 500
    
    def test_get_collect_with_various_amounts(self, client, mock_cost_functions):
        """Test cost collection with various amount types"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 0.0},
            {"date": "2026-07-02", "amount": 100.50},
            {"date": "2026-07-03", "amount": 9999.99},
            {"date": "2026-07-04", "amount": -50.0}  # negative amount
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["costs"]) == 4


class TestGetForecast:
    """Test get_forecast endpoint"""
    
    def test_get_forecast_default_days(self, client, mock_cost_functions):
        """Test forecast with default days parameter"""
        mock_forecast_data = [
            {"date": "2026-07-02", "predicted_amount": 105.0},
            {"date": "2026-07-03", "predicted_amount": 110.0}
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast")
        
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert "forecast" in data
        assert data["days"] == 30  # default value
        mock_cost_functions['forecast_costs'].assert_called_once_with(30)
    
    def test_get_forecast_custom_days(self, client, mock_cost_functions):
        """Test forecast with custom days parameter"""
        mock_forecast_data = [
            {"date": "2026-07-02", "predicted_amount": 105.0}
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 7
        mock_cost_functions['forecast_costs'].assert_called_once_with(7)
    
    def test_get_forecast_single_day(self, client, mock_cost_functions):
        """Test forecast for single day"""
        mock_forecast_data = [
            {"date": "2026-07-02", "predicted_amount": 105.0}
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=1")
        
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 1
        assert len(data["forecast"]) == 1
    
    def test_get_forecast_long_period(self, client, mock_cost_functions):
        """Test forecast for long period"""
        mock_forecast_data = [
            {"date": f"2026-07-{i:02d}", "predicted_amount": 100.0 + i}
            for i in range(1, 366)
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=365")
        
        assert response.status_code == 200
        data = response.json()
        assert data["days"] == 365
        assert len(data["forecast"]) == 365
    
    def test_get_forecast_empty_data(self, client, mock_cost_functions):
        """Test forecast with no data"""
        mock_cost_functions['forecast_costs'].return_value = []
        
        response = client.get("/api/cost/forecast?days=30")
        
        assert response.status_code == 404
        assert "Forecast data unavailable" in response.json()["detail"]
    
    def test_get_forecast_none_data(self, client, mock_cost_functions):
        """Test forecast with None return"""
        mock_cost_functions['forecast_costs'].return_value = None
        
        response = client.get("/api/cost/forecast?days=30")
        
        assert response.status_code == 404
        assert "Forecast data unavailable" in response.json()["detail"]
    
    def test_get_forecast_zero_days(self, client, mock_cost_functions):
        """Test forecast with zero days"""
        mock_forecast_data = []
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=0")
        
        # Should handle zero days gracefully
        assert response.status_code in [200, 404]
    
    def test_get_forecast_negative_days(self, client, mock_cost_functions):
        """Test forecast with negative days"""
        mock_forecast_data = []
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=-7")
        
        # Should handle negative days gracefully
        assert response.status_code in [200, 404, 422]
    
    def test_get_forecast_function_error(self, client, mock_cost_functions):
        """Test forecast with function error"""
        mock_cost_functions['forecast_costs'].side_effect = Exception("Forecast failed")
        
        response = client.get("/api/cost/forecast?days=30")
        
        assert response.status_code == 500
    
    def test_get_forecast_with_none_days_param(self, client, mock_cost_functions):
        """Test forecast with None days parameter"""
        mock_forecast_data = [{"date": "2026-07-02", "predicted_amount": 105.0}]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=")
        
        # Should default to 30 when days is None/empty
        assert response.status_code in [200, 422]


class TestGetBudget:
    """Test get_budget endpoint"""
    
    def test_get_budget_success(self, client, mock_cost_functions):
        """Test successful budget status retrieval"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 500.0,
            "remaining": 500.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["budget"] == 1000.0
        assert data["used"] == 500.0
        assert data["remaining"] == 500.0
        assert data["status"] == "normal"
        mock_cost_functions['budget_status'].assert_called_once()
    
    def test_get_budget_warning_status(self, client, mock_cost_functions):
        """Test budget status with warning"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 850.0,
            "remaining": 150.0,
            "status": "warning"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "warning"
    
    def test_get_budget_critical_status(self, client, mock_cost_functions):
        """Test budget status with critical"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 950.0,
            "remaining": 50.0,
            "status": "critical"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "critical"
    
    def test_get_budget_exceeded(self, client, mock_cost_functions):
        """Test budget when exceeded"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 1200.0,
            "remaining": -200.0,
            "status": "exceeded"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["remaining"] == -200.0
    
    def test_get_budget_zero_usage(self, client, mock_cost_functions):
        """Test budget with zero usage"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 0.0,
            "remaining": 1000.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["used"] == 0.0
    
    def test_get_budget_full_usage(self, client, mock_cost_functions):
        """Test budget with full usage"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 1000.0,
            "remaining": 0.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["remaining"] == 0.0
    
    def test_get_budget_with_recommendations(self, client, mock_cost_functions):
        """Test budget status with recommendations"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 600.0,
            "remaining": 400.0,
            "status": "normal",
            "recommendations": [
                "Optimize resource usage",
                "Consider reserved instances"
            ]
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert len(data["recommendations"]) == 2
    
    def test_get_budget_function_error(self, client, mock_cost_functions):
        """Test budget status with function error"""
        mock_cost_functions['budget_status'].side_effect = Exception("Budget check failed")
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 500
    
    def test_get_budget_with_breakdown(self, client, mock_cost_functions):
        """Test budget status with cost breakdown"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 600.0,
            "remaining": 400.0,
            "status": "normal",
            "breakdown": {
                "compute": 300.0,
                "storage": 150.0,
                "network": 100.0,
                "other": 50.0
            }
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert "breakdown" in data
        assert data["breakdown"]["compute"] == 300.0


class TestIntegrationScenarios:
    """Test integration scenarios"""
    
    def test_full_cost_monitoring_workflow(self, client, mock_cost_functions):
        """Test complete cost monitoring workflow"""
        # Collect current costs
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 100.0},
            {"date": "2026-07-02", "amount": 150.0}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        assert response.status_code == 200
        assert len(response.json()["costs"]) == 2
        
        # Check budget status
        mock_budget_data = {
            "budget": 1000.0,
            "used": 250.0,
            "remaining": 750.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        assert response.status_code == 200
        assert response.json()["status"] == "normal"
        
        # Get forecast
        mock_forecast_data = [
            {"date": "2026-07-03", "predicted_amount": 120.0},
            {"date": "2026-07-04", "predicted_amount": 130.0}
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=2")
        assert response.status_code == 200
        assert len(response.json()["forecast"]) == 2
    
    def test_budget_alert_workflow(self, client, mock_cost_functions):
        """Test budget alert scenario"""
        # Check budget when approaching limit
        mock_budget_data = {
            "budget": 1000.0,
            "used": 900.0,
            "remaining": 100.0,
            "status": "warning"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        assert response.status_code == 200
        assert response.json()["status"] == "warning"
        
        # Get forecast to see if budget will be exceeded
        mock_forecast_data = [
            {"date": "2026-07-03", "predicted_amount": 150.0}
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=1")
        assert response.status_code == 200


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_large_budget(self, client, mock_cost_functions):
        """Test with very large budget values"""
        mock_budget_data = {
            "budget": 1000000.0,
            "used": 500000.0,
            "remaining": 500000.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        
        assert response.status_code == 200
        data = response.json()
        assert data["budget"] == 1000000.0
    
    def test_very_small_amounts(self, client, mock_cost_functions):
        """Test with very small amount values"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 0.01},
            {"date": "2026-07-02", "amount": 0.001}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
    
    def test_negative_costs(self, client, mock_cost_functions):
        """Test with negative cost values (refunds)"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": -50.0},
            {"date": "2026-07-02", "amount": 100.0}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert data["costs"][0]["amount"] == -50.0
    
    def test_fractional_days(self, client, mock_cost_functions):
        """Test forecast with fractional days (should be handled)"""
        mock_forecast_data = []
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=7.5")
        
        # Should handle fractional days or convert to int
        assert response.status_code in [200, 422]
    
    def test_unicode_in_cost_data(self, client, mock_cost_functions):
        """Test with unicode characters in cost data"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 100.0, "description": "测试成本"},
            {"date": "2026-07-02", "amount": 150.0, "description": "テスト"}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200


class TestConcurrentOperations:
    """Test concurrent operations"""
    
    def test_concurrent_cost_collection(self, client, mock_cost_functions):
        """Test multiple concurrent cost collection requests"""
        mock_cost_data = [{"date": "2026-07-01", "amount": 100.0}]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        # Make multiple requests
        for i in range(5):
            response = client.get("/api/cost/collect")
            assert response.status_code == 200
        
        assert mock_cost_functions['collect_costs'].call_count == 5
    
    def test_concurrent_forecast_requests(self, client, mock_cost_functions):
        """Test multiple concurrent forecast requests"""
        mock_forecast_data = [{"date": "2026-07-02", "predicted_amount": 105.0}]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        # Make multiple requests with different parameters
        for days in [7, 14, 30, 60, 90]:
            response = client.get(f"/api/cost/forecast?days={days}")
            assert response.status_code == 200
        
        assert mock_cost_functions['forecast_costs'].call_count == 5


class TestDateFormats:
    """Test different date formats in responses"""
    
    def test_iso_date_format(self, client, mock_cost_functions):
        """Test ISO 8601 date format"""
        mock_cost_data = [
            {"date": "2026-07-01T00:00:00Z", "amount": 100.0}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
    
    def test_various_date_formats(self, client, mock_cost_functions):
        """Test various date formats"""
        mock_cost_data = [
            {"date": "2026-07-01", "amount": 100.0},
            {"date": "2026/07/02", "amount": 150.0},
            {"date": "01-07-2026", "amount": 120.0}
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200


class TestErrorRecovery:
    """Test error recovery scenarios"""
    
    def test_temporary_error_recovery(self, client, mock_cost_functions):
        """Test recovery from temporary error"""
        # First request fails
        mock_cost_functions['collect_costs'].side_effect = Exception("Temporary error")
        response = client.get("/api/cost/collect")
        assert response.status_code == 500
        
        # Second request succeeds
        mock_cost_data = [{"date": "2026-07-01", "amount": 100.0}]
        mock_cost_functions['collect_costs'].side_effect = None
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        assert response.status_code == 200
    
    def test_forecast_fallback(self, client, mock_cost_functions):
        """Test forecast fallback when long period fails"""
        # Long period forecast fails
        mock_cost_functions['forecast_costs'].side_effect = Exception("Too long")
        response = client.get("/api/cost/forecast?days=365")
        assert response.status_code == 500
        
        # Shorter period succeeds
        mock_forecast_data = [{"date": "2026-07-02", "predicted_amount": 105.0}]
        mock_cost_functions['forecast_costs'].side_effect = None
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=7")
        assert response.status_code == 200


class TestResponseStructures:
    """Test response structure validation"""
    
    def test_collect_response_structure(self, client, mock_cost_functions):
        """Test cost collection response structure"""
        mock_cost_data = [{"date": "2026-07-01", "amount": 100.0}]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        data = response.json()
        
        assert "costs" in data
        assert isinstance(data["costs"], list)
        assert len(data["costs"]) > 0
        assert "date" in data["costs"][0]
        assert "amount" in data["costs"][0]
    
    def test_forecast_response_structure(self, client, mock_cost_functions):
        """Test forecast response structure"""
        mock_forecast_data = [{"date": "2026-07-02", "predicted_amount": 105.0}]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=1")
        data = response.json()
        
        assert "days" in data
        assert "forecast" in data
        assert isinstance(data["forecast"], list)
        assert isinstance(data["days"], int)
    
    def test_budget_response_structure(self, client, mock_cost_functions):
        """Test budget response structure"""
        mock_budget_data = {
            "budget": 1000.0,
            "used": 500.0,
            "remaining": 500.0,
            "status": "normal"
        }
        mock_cost_functions['budget_status'].return_value = mock_budget_data
        
        response = client.get("/api/cost/budget")
        data = response.json()
        
        assert "budget" in data
        assert "used" in data
        assert "remaining" in data
        assert "status" in data
        assert isinstance(data["budget"], (int, float))
        assert isinstance(data["used"], (int, float))
        assert isinstance(data["remaining"], (int, float))
        assert isinstance(data["status"], str)


class TestPerformanceScenarios:
    """Test performance-related scenarios"""
    
    def test_large_dataset_handling(self, client, mock_cost_functions):
        """Test handling of large datasets"""
        # Generate large dataset
        mock_cost_data = [
            {"date": f"2026-07-{i%30+1:02d}", "amount": 100.0 + i}
            for i in range(1000)
        ]
        mock_cost_functions['collect_costs'].return_value = mock_cost_data
        
        response = client.get("/api/cost/collect")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["costs"]) == 1000
    
    def test_forecast_performance(self, client, mock_cost_functions):
        """Test forecast performance with various periods"""
        mock_forecast_data = [
            {"date": f"2026-07-{i:02d}", "predicted_amount": 100.0}
            for i in range(1, 366)
        ]
        mock_cost_functions['forecast_costs'].return_value = mock_forecast_data
        
        response = client.get("/api/cost/forecast?days=365")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["forecast"]) == 365
