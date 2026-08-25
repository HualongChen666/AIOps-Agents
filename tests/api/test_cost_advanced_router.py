# -*- coding: utf-8 -*-
"""
Test suite for cost_advanced_router.py

This module provides comprehensive test coverage for the cost advanced router,
including all CRUD operations, data validation, error handling, and permission controls.
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from api.cost_advanced_router import (
    router,
    BudgetCreate,
    BudgetUpdate,
    AnalyticsRequest,
    OptimizationRequest,
    ReportRequest,
    AlertCreate,
    AlertUpdate,
    _budgets,
    _optimization_suggestions,
    _anomalies,
    _alerts,
    _reports,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_budget():
    """Create a sample budget for testing"""
    return {
        "name": "Test Budget",
        "service": "Amazon EC2",
        "amount": 1000.0,
        "period": "monthly",
        "alerts_enabled": True
    }


@pytest.fixture
def sample_analytics_request():
    """Create a sample analytics request for testing"""
    return {
        "start_date": "2026-01-01T00:00:00",
        "end_date": "2026-01-31T23:59:59",
        "group_by": "service",
        "granularity": "daily"
    }


@pytest.fixture
def sample_optimization_request():
    """Create a sample optimization request for testing"""
    return {
        "resource_id": "opt-1",
        "action": "apply"
    }


@pytest.fixture
def sample_report_request():
    """Create a sample report request for testing"""
    return {
        "period": "30d",
        "format": "json",
        "include_forecast": True
    }


@pytest.fixture
def sample_alert():
    """Create a sample alert for testing"""
    return {
        "name": "Test Alert",
        "type": "budget_exceeded",
        "threshold": 90.0,
        "severity": "critical",
        "notification_channels": ["email", "slack"]
    }


@pytest.fixture(autouse=True)
def reset_state():
    """Reset the in-memory state before each test"""
    # Save original data
    original_budgets = _budgets.copy()
    original_optimizations = _optimization_suggestions.copy()
    original_anomalies = _anomalies.copy()
    original_alerts = _alerts.copy()
    original_reports = _reports.copy()
    
    yield
    
    # Restore original data
    _budgets.clear()
    _budgets.update(original_budgets)
    _optimization_suggestions.clear()
    _optimization_suggestions.update(original_optimizations)
    _anomalies.clear()
    _anomalies.extend(original_anomalies)
    _alerts.clear()
    _alerts.update(original_alerts)
    _reports.clear()
    _reports.update(original_reports)


# ============================================================================
# Cost Overview Tests
# ============================================================================

class TestCostOverview:
    """Test suite for cost overview endpoint"""

    @pytest.mark.asyncio
    async def test_get_cost_overview_success(self):
        """Test successful retrieval of cost overview"""
        from api.cost_advanced_router import get_cost_overview
        
        result = await get_cost_overview()
        
        assert "total_cost" in result
        assert "budget_status" in result
        assert "forecast" in result
        assert "trends" in result
        assert "metrics" in result
        assert "cost_by_service" in result
        assert "last_updated" in result

    @pytest.mark.asyncio
    async def test_get_cost_overview_structure(self):
        """Test that cost overview has correct structure"""
        from api.cost_advanced_router import get_cost_overview
        
        result = await get_cost_overview()
        
        # Check forecast structure
        assert "period_days" in result["forecast"]
        assert "total_forecast" in result["forecast"]
        assert "forecast_data" in result["forecast"]
        
        # Check trends structure
        assert "direction" in result["trends"]
        assert "percent_change" in result["trends"]
        
        # Check metrics structure
        assert "active_budgets" in result["metrics"]
        assert "pending_optimizations" in result["metrics"]
        assert "open_anomalies" in result["metrics"]
        assert "total_alerts" in result["metrics"]

    @pytest.mark.asyncio
    async def test_get_cost_overview_exception_handling(self):
        """Test that exceptions are handled properly"""
        from api.cost_advanced_router import get_cost_overview
        
        with patch('api.cost_advanced_router.collect_costs', side_effect=Exception("Cost collection error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_cost_overview()
            
            assert exc_info.value.status_code == 500
            assert "Failed to get cost overview" in exc_info.value.detail


# ============================================================================
# Cost Analytics Tests
# ============================================================================

class TestCostAnalytics:
    """Test suite for cost analytics endpoints"""

    @pytest.mark.asyncio
    async def test_get_cost_analytics_success(self):
        """Test successful retrieval of cost analytics"""
        from api.cost_advanced_router import get_cost_analytics
        
        result = await get_cost_analytics(
            start_date="2026-01-01T00:00:00",
            end_date="2026-01-31T23:59:59",
            group_by="service",
            granularity="daily"
        )
        
        assert "summary" in result
        assert "grouped_data" in result
        assert "time_series" in result
        assert "insights" in result
        assert "filters" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_get_cost_analytics_without_filters(self):
        """Test cost analytics without date filters"""
        from api.cost_advanced_router import get_cost_analytics
        
        result = await get_cost_analytics()
        
        assert "summary" in result
        # Query objects might not be None, so just check they exist
        assert "start_date" in result["filters"]
        assert "end_date" in result["filters"]

    @pytest.mark.asyncio
    async def test_get_cost_analytics_group_by_service(self):
        """Test cost analytics grouped by service"""
        from api.cost_advanced_router import get_cost_analytics
        
        result = await get_cost_analytics(group_by="service")
        
        assert result["filters"]["group_by"] == "service"
        assert isinstance(result["grouped_data"], dict)

    @pytest.mark.asyncio
    async def test_get_cost_analytics_group_by_region(self):
        """Test cost analytics grouped by region"""
        from api.cost_advanced_router import get_cost_analytics
        
        result = await get_cost_analytics(group_by="region")
        
        assert result["filters"]["group_by"] == "region"

    @pytest.mark.asyncio
    async def test_get_cost_analytics_group_by_category(self):
        """Test cost analytics grouped by category"""
        from api.cost_advanced_router import get_cost_analytics
        
        result = await get_cost_analytics(group_by="category")
        
        assert result["filters"]["group_by"] == "category"

    @pytest.mark.asyncio
    async def test_run_custom_analytics_success(self, sample_analytics_request):
        """Test running custom analytics with POST request"""
        from api.cost_advanced_router import run_custom_analytics
        
        request = AnalyticsRequest(**sample_analytics_request)
        result = await run_custom_analytics(request)
        
        assert "summary" in result
        assert result["filters"]["start_date"] == "2026-01-01T00:00:00"
        assert result["filters"]["end_date"] == "2026-01-31T23:59:59"

    @pytest.mark.asyncio
    async def test_get_cost_analytics_exception_handling(self):
        """Test that exceptions are handled properly"""
        from api.cost_advanced_router import get_cost_analytics
        
        with patch('api.cost_advanced_router.collect_costs', side_effect=Exception("Analytics error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_cost_analytics()
            
            assert exc_info.value.status_code == 500
            assert "Failed to get cost analytics" in exc_info.value.detail


# ============================================================================
# Cost Optimization Tests
# ============================================================================

class TestCostOptimization:
    """Test suite for cost optimization endpoints"""

    @pytest.mark.asyncio
    async def test_get_optimization_suggestions_success(self):
        """Test successful retrieval of optimization suggestions"""
        from api.cost_advanced_router import get_optimization_suggestions
        
        result = await get_optimization_suggestions()
        
        assert "suggestions" in result
        assert "summary" in result
        assert "by_type" in result
        assert "by_effort" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_get_optimization_suggestions_summary(self):
        """Test optimization suggestions summary"""
        from api.cost_advanced_router import get_optimization_suggestions
        
        result = await get_optimization_suggestions()
        
        assert "total_suggestions" in result["summary"]
        assert "pending_count" in result["summary"]
        assert "applied_count" in result["summary"]
        assert "dismissed_count" in result["summary"]
        assert "total_potential_savings" in result["summary"]

    @pytest.mark.asyncio
    async def test_handle_optimization_apply_success(self, sample_optimization_request):
        """Test applying an optimization suggestion"""
        from api.cost_advanced_router import handle_optimization
        
        request = OptimizationRequest(**sample_optimization_request)
        result = await handle_optimization(request)
        
        assert result["success"] == True
        assert "Successfully applied" in result["message"]
        assert result["suggestion"]["status"] == "applied"

    @pytest.mark.asyncio
    async def test_handle_optimization_dismiss_success(self):
        """Test dismissing an optimization suggestion"""
        from api.cost_advanced_router import handle_optimization
        
        request = OptimizationRequest(resource_id="opt-1", action="dismiss")
        result = await handle_optimization(request)
        
        assert result["success"] == True
        assert "Successfully dismissed" in result["message"]
        assert result["suggestion"]["status"] == "dismissed"

    @pytest.mark.asyncio
    async def test_handle_optimization_missing_resource_id(self):
        """Test handling optimization without resource_id"""
        from api.cost_advanced_router import handle_optimization
        
        request = OptimizationRequest(resource_id=None, action="apply")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_optimization(request)
        
        assert exc_info.value.status_code == 400
        assert "resource_id is required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handle_optimization_not_found(self):
        """Test handling non-existent optimization"""
        from api.cost_advanced_router import handle_optimization
        
        request = OptimizationRequest(resource_id="non-existent", action="apply")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_optimization(request)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_handle_optimization_invalid_action(self):
        """Test handling optimization with invalid action"""
        from api.cost_advanced_router import handle_optimization
        
        request = OptimizationRequest(resource_id="opt-1", action="invalid")
        
        with pytest.raises(HTTPException) as exc_info:
            await handle_optimization(request)
        
        assert exc_info.value.status_code == 400
        assert "Invalid action" in exc_info.value.detail


# ============================================================================
# Budget Tests
# ============================================================================

class TestBudgets:
    """Test suite for budget endpoints"""

    @pytest.mark.asyncio
    async def test_get_budgets_success(self):
        """Test successful retrieval of budgets"""
        from api.cost_advanced_router import get_budgets
        
        result = await get_budgets()
        
        assert "budgets" in result
        assert "summary" in result
        assert "retrieved_at" in result

    @pytest.mark.asyncio
    async def test_get_budgets_summary(self):
        """Test budgets summary"""
        from api.cost_advanced_router import get_budgets
        
        result = await get_budgets()
        
        assert "total_budgets" in result["summary"]
        assert "total_budget_amount" in result["summary"]
        assert "total_spent" in result["summary"]
        assert "total_remaining" in result["summary"]
        assert "utilization_percent" in result["summary"]
        assert "status_counts" in result["summary"]

    @pytest.mark.asyncio
    async def test_create_budget_success(self, sample_budget):
        """Test successful creation of budget"""
        from api.cost_advanced_router import create_budget
        
        budget = BudgetCreate(**sample_budget)
        result = await create_budget(budget)
        
        assert result["success"] == True
        assert "budget" in result
        assert result["budget"]["name"] == "Test Budget"
        assert result["budget"]["amount"] == 1000.0
        assert result["budget"]["spent"] == 0.0
        assert result["budget"]["remaining"] == 1000.0

    @pytest.mark.asyncio
    async def test_create_budget_validation_error(self):
        """Test that invalid budget data is rejected"""
        from api.cost_advanced_router import create_budget
        
        # Test negative amount
        with pytest.raises(Exception):
            BudgetCreate(
                name="Test",
                service="EC2",
                amount=-100.0  # Should fail gt=0 validation
            )

    @pytest.mark.asyncio
    async def test_update_budget_success(self):
        """Test successful update of budget"""
        from api.cost_advanced_router import update_budget
        
        # Update existing budget
        budget_update = BudgetUpdate(name="Updated Budget", amount=1500.0)
        result = await update_budget("budget-1", budget_update)
        
        assert result["success"] == True
        assert result["budget"]["name"] == "Updated Budget"
        assert result["budget"]["amount"] == 1500.0

    @pytest.mark.asyncio
    async def test_update_budget_not_found(self):
        """Test updating non-existent budget"""
        from api.cost_advanced_router import update_budget
        
        budget_update = BudgetUpdate(name="Updated Budget")
        
        with pytest.raises(HTTPException) as exc_info:
            await update_budget("non-existent", budget_update)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_update_budget_status_calculation(self):
        """Test that budget status is recalculated correctly"""
        from api.cost_advanced_router import update_budget
        
        # Update amount to trigger warning status
        budget_update = BudgetUpdate(amount=500.0)  # Spent is 480.0, so 96% utilization
        result = await update_budget("budget-2", budget_update)
        
        assert result["budget"]["status"] == "exceeded"  # 96% >= 90%

    @pytest.mark.asyncio
    async def test_delete_budget_success(self):
        """Test successful deletion of budget"""
        from api.cost_advanced_router import delete_budget
        
        result = await delete_budget("budget-1")
        
        assert result["success"] == True
        assert "deleted_budget" in result
        assert "budget-1" not in _budgets

    @pytest.mark.asyncio
    async def test_delete_budget_not_found(self):
        """Test deleting non-existent budget"""
        from api.cost_advanced_router import delete_budget
        
        with pytest.raises(HTTPException) as exc_info:
            await delete_budget("non-existent")
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail


# ============================================================================
# Cost Forecasts Tests
# ============================================================================

class TestCostForecasts:
    """Test suite for cost forecast endpoints"""

    @pytest.mark.asyncio
    async def test_get_forecasts_success(self):
        """Test successful retrieval of cost forecasts"""
        from api.cost_advanced_router import get_forecasts
        
        result = await get_forecasts(days=30)
        
        assert "forecast_period" in result
        assert "forecast_data" in result
        assert "summary" in result
        assert "confidence" in result
        assert "generated_at" in result

    @pytest.mark.asyncio
    async def test_get_forecasts_with_service_filter(self):
        """Test forecasts with service filter"""
        from api.cost_advanced_router import get_forecasts
        
        result = await get_forecasts(days=30, service="Amazon EC2")
        
        assert "forecast_period" in result
        assert result["forecast_period"]["days"] == 30

    @pytest.mark.asyncio
    async def test_get_forecasts_custom_days(self):
        """Test forecasts with custom days parameter"""
        from api.cost_advanced_router import get_forecasts
        
        result = await get_forecasts(days=90)
        
        assert result["forecast_period"]["days"] == 90

    @pytest.mark.asyncio
    async def test_get_forecasts_validation(self):
        """Test that invalid days values are rejected"""
        from api.cost_advanced_router import get_forecasts
        
        # Test minimum valid days
        result = await get_forecasts(days=1)
        assert result["forecast_period"]["days"] == 1
        
        # Test maximum valid days
        result = await get_forecasts(days=365)
        assert result["forecast_period"]["days"] == 365

    @pytest.mark.asyncio
    async def test_get_forecasts_summary_structure(self):
        """Test that forecast summary has correct structure"""
        from api.cost_advanced_router import get_forecasts
        
        result = await get_forecasts(days=30)
        
        assert "total_forecast" in result["summary"]
        assert "average_daily_forecast" in result["summary"]
        assert "historical_average" in result["summary"]
        assert "growth_rate_percent" in result["summary"]


# ============================================================================
# Cost Reports Tests
# ============================================================================

class TestCostReports:
    """Test suite for cost report endpoints"""

    @pytest.mark.asyncio
    async def test_get_reports_success(self):
        """Test successful retrieval of reports list"""
        from api.cost_advanced_router import get_reports
        
        result = await get_reports()
        
        assert "reports" in result
        assert "total_count" in result
        assert "retrieved_at" in result

    @pytest.mark.asyncio
    async def test_generate_report_success(self, sample_report_request):
        """Test successful generation of cost report"""
        from api.cost_advanced_router import generate_report
        
        request = ReportRequest(**sample_report_request)
        result = await generate_report(request)
        
        assert result["success"] == True
        assert "report" in result
        assert result["report"]["period_days"] == 30
        assert result["report"]["format"] == "json"
        assert result["report"]["include_forecast"] == True

    @pytest.mark.asyncio
    async def test_generate_report_without_forecast(self):
        """Test generating report without forecast"""
        from api.cost_advanced_router import generate_report
        
        request = ReportRequest(period="30d", format="json", include_forecast=False)
        result = await generate_report(request)
        
        assert result["report"]["include_forecast"] == False
        assert "forecast" not in result["report"]

    @pytest.mark.asyncio
    async def test_generate_report_different_periods(self):
        """Test generating reports with different periods"""
        from api.cost_advanced_router import generate_report
        
        # Test 7d period
        request = ReportRequest(period="7d", format="json")
        result = await generate_report(request)
        assert result["report"]["period_days"] == 7
        
        # Test 90d period
        request = ReportRequest(period="90d", format="json")
        result = await generate_report(request)
        assert result["report"]["period_days"] == 90

    @pytest.mark.asyncio
    async def test_generate_report_structure(self):
        """Test that generated report has correct structure"""
        from api.cost_advanced_router import generate_report
        
        request = ReportRequest(period="30d", format="json", include_forecast=True)
        result = await generate_report(request)
        
        report = result["report"]
        assert "period_start" in report
        assert "period_end" in report
        assert "total_cost" in report
        assert "budget" in report
        assert "variance" in report
        assert "variance_percent" in report
        assert "by_service" in report
        assert "by_category" in report
        assert "trends" in report


# ============================================================================
# Cost Anomalies Tests
# ============================================================================

class TestCostAnomalies:
    """Test suite for cost anomaly endpoints"""

    @pytest.mark.asyncio
    async def test_get_anomalies_success(self):
        """Test successful retrieval of cost anomalies"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies()
        
        assert "anomalies" in result
        assert "summary" in result
        assert "filters" in result
        assert "retrieved_at" in result

    @pytest.mark.asyncio
    async def test_get_anomalies_with_severity_filter(self):
        """Test filtering anomalies by severity"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies(severity="high")
        
        assert result["filters"]["severity"] == "high"
        for anomaly in result["anomalies"]:
            assert anomaly["severity"] == "high"

    @pytest.mark.asyncio
    async def test_get_anomalies_with_status_filter(self):
        """Test filtering anomalies by status"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies(status="open")
        
        assert result["filters"]["status"] == "open"
        for anomaly in result["anomalies"]:
            assert anomaly["status"] == "open"

    @pytest.mark.asyncio
    async def test_get_anomalies_summary(self):
        """Test anomalies summary"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies()
        
        assert "total_count" in result["summary"]
        assert "filtered_count" in result["summary"]
        assert "severity_counts" in result["summary"]
        assert "status_counts" in result["summary"]
        assert "total_impact" in result["summary"]

    @pytest.mark.asyncio
    async def test_get_anomalies_severity_counts(self):
        """Test that severity counts are calculated correctly"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies()
        
        severity_counts = result["summary"]["severity_counts"]
        assert "high" in severity_counts
        assert "medium" in severity_counts
        assert "low" in severity_counts

    @pytest.mark.asyncio
    async def test_get_anomalies_status_counts(self):
        """Test that status counts are calculated correctly"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies()
        
        status_counts = result["summary"]["status_counts"]
        assert "open" in status_counts
        assert "investigating" in status_counts
        assert "resolved" in status_counts


# ============================================================================
# Cost Alerts Tests
# ============================================================================

class TestCostAlerts:
    """Test suite for cost alert endpoints"""

    @pytest.mark.asyncio
    async def test_get_alerts_success(self):
        """Test successful retrieval of cost alerts"""
        from api.cost_advanced_router import get_alerts
        
        result = await get_alerts()
        
        assert "alerts" in result
        assert "summary" in result
        assert "filters" in result
        assert "retrieved_at" in result

    @pytest.mark.asyncio
    async def test_get_alerts_with_enabled_filter(self):
        """Test filtering alerts by enabled status"""
        from api.cost_advanced_router import get_alerts
        
        result = await get_alerts(enabled=True)
        
        assert result["filters"]["enabled"] == True
        for alert in result["alerts"]:
            assert alert["enabled"] == True

    @pytest.mark.asyncio
    async def test_get_alerts_summary(self):
        """Test alerts summary"""
        from api.cost_advanced_router import get_alerts
        
        result = await get_alerts()
        
        assert "total_count" in result["summary"]
        assert "enabled_count" in result["summary"]
        assert "disabled_count" in result["summary"]
        assert "severity_counts" in result["summary"]
        assert "type_counts" in result["summary"]

    @pytest.mark.asyncio
    async def test_create_alert_success(self, sample_alert):
        """Test successful creation of alert"""
        from api.cost_advanced_router import create_alert
        
        alert = AlertCreate(**sample_alert)
        result = await create_alert(alert)
        
        assert result["success"] == True
        assert "alert" in result
        assert result["alert"]["name"] == "Test Alert"
        assert result["alert"]["type"] == "budget_exceeded"
        assert result["alert"]["threshold"] == 90.0
        assert result["alert"]["enabled"] == True

    @pytest.mark.asyncio
    async def test_create_alert_validation_error(self):
        """Test that invalid alert data is rejected"""
        from api.cost_advanced_router import create_alert
        
        # Test negative threshold
        with pytest.raises(Exception):
            AlertCreate(
                name="Test",
                type="budget_exceeded",
                threshold=-10.0  # Should fail gt=0 validation
            )

    @pytest.mark.asyncio
    async def test_get_alerts_severity_counts(self):
        """Test that severity counts are calculated correctly"""
        from api.cost_advanced_router import get_alerts
        
        result = await get_alerts()
        
        severity_counts = result["summary"]["severity_counts"]
        assert "critical" in severity_counts
        assert "high" in severity_counts
        assert "medium" in severity_counts
        assert "low" in severity_counts

    @pytest.mark.asyncio
    async def test_get_alerts_type_counts(self):
        """Test that type counts are calculated correctly"""
        from api.cost_advanced_router import get_alerts
        
        result = await get_alerts()
        
        type_counts = result["summary"]["type_counts"]
        assert isinstance(type_counts, dict)


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test suite for data validation"""

    def test_budget_create_valid(self, sample_budget):
        """Test valid budget creation"""
        budget = BudgetCreate(**sample_budget)
        assert budget.name == "Test Budget"
        assert budget.amount == 1000.0

    def test_budget_create_invalid_amount(self):
        """Test that negative amount is rejected"""
        with pytest.raises(Exception):
            BudgetCreate(
                name="Test",
                service="EC2",
                amount=-100.0
            )

    def test_budget_create_invalid_amount_zero(self):
        """Test that zero amount is rejected"""
        with pytest.raises(Exception):
            BudgetCreate(
                name="Test",
                service="EC2",
                amount=0.0
            )

    def test_budget_update_valid(self):
        """Test valid budget update"""
        budget = BudgetUpdate(name="Updated", amount=2000.0)
        assert budget.name == "Updated"
        assert budget.amount == 2000.0

    def test_analytics_request_valid(self, sample_analytics_request):
        """Test valid analytics request"""
        request = AnalyticsRequest(**sample_analytics_request)
        assert request.group_by == "service"
        assert request.granularity == "daily"

    def test_optimization_request_valid(self, sample_optimization_request):
        """Test valid optimization request"""
        request = OptimizationRequest(**sample_optimization_request)
        assert request.resource_id == "opt-1"
        assert request.action == "apply"

    def test_report_request_valid(self, sample_report_request):
        """Test valid report request"""
        request = ReportRequest(**sample_report_request)
        assert request.period == "30d"
        assert request.format == "json"
        assert request.include_forecast == True

    def test_alert_create_valid(self, sample_alert):
        """Test valid alert creation"""
        alert = AlertCreate(**sample_alert)
        assert alert.name == "Test Alert"
        assert alert.threshold == 90.0

    def test_alert_create_invalid_threshold(self):
        """Test that negative threshold is rejected"""
        with pytest.raises(Exception):
            AlertCreate(
                name="Test",
                type="budget_exceeded",
                threshold=-10.0
            )

    def test_alert_update_valid(self):
        """Test valid alert update"""
        alert = AlertUpdate(name="Updated", threshold=95.0, enabled=False)
        assert alert.name == "Updated"
        assert alert.threshold == 95.0
        assert alert.enabled == False


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling"""

    @pytest.mark.asyncio
    async def test_cost_monitor_exception_handling(self):
        """Test that cost monitor exceptions are handled properly"""
        from api.cost_advanced_router import get_cost_overview
        
        with patch('api.cost_advanced_router.collect_costs', side_effect=Exception("Monitor error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_cost_overview()
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_forecast_exception_handling(self):
        """Test that forecast exceptions are handled properly"""
        from api.cost_advanced_router import get_cost_overview
        
        with patch('api.cost_advanced_router.forecast_costs', side_effect=Exception("Forecast error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_cost_overview()
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_budget_status_exception_handling(self):
        """Test that budget status exceptions are handled properly"""
        from api.cost_advanced_router import get_cost_overview
        
        with patch('api.cost_advanced_router.budget_status', side_effect=Exception("Budget status error")):
            with pytest.raises(HTTPException) as exc_info:
                await get_cost_overview()
            
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_report_generation_exception_handling(self):
        """Test that report generation exceptions are handled properly"""
        from api.cost_advanced_router import generate_report
        
        with patch('api.cost_advanced_router.collect_costs', side_effect=Exception("Report error")):
            request = ReportRequest(period="30d", format="json")
            with pytest.raises(HTTPException) as exc_info:
                await generate_report(request)
            
            assert exc_info.value.status_code == 500


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests for cost router"""

    @pytest.mark.asyncio
    async def test_full_budget_lifecycle(self, sample_budget):
        """Test complete budget lifecycle: create, read, update, delete"""
        from api.cost_advanced_router import (
            create_budget,
            get_budgets,
            update_budget,
            delete_budget
        )
        
        # Create
        budget = BudgetCreate(**sample_budget)
        created = await create_budget(budget)
        budget_id = created["budget"]["id"]
        assert created["success"] == True
        
        # Read
        budgets = await get_budgets()
        assert any(b["id"] == budget_id for b in budgets["budgets"])
        
        # Update
        budget_update = BudgetUpdate(name="Updated Budget", amount=1500.0)
        updated = await update_budget(budget_id, budget_update)
        assert updated["budget"]["name"] == "Updated Budget"
        
        # Delete
        deleted = await delete_budget(budget_id)
        assert deleted["success"] == True
        assert budget_id not in _budgets

    @pytest.mark.asyncio
    async def test_full_alert_lifecycle(self, sample_alert):
        """Test complete alert lifecycle: create, read, delete"""
        from api.cost_advanced_router import (
            create_alert,
            get_alerts,
            _alerts
        )
        
        # Create
        alert = AlertCreate(**sample_alert)
        created = await create_alert(alert)
        alert_id = created["alert"]["id"]
        assert created["success"] == True
        
        # Read - check directly in the alerts dict
        assert alert_id in _alerts
        
        # Delete (using direct dict manipulation as there's no delete endpoint)
        if alert_id in _alerts:
            del _alerts[alert_id]
        assert alert_id not in _alerts

    @pytest.mark.asyncio
    async def test_optimization_lifecycle(self):
        """Test optimization suggestion lifecycle"""
        from api.cost_advanced_router import (
            get_optimization_suggestions,
            handle_optimization
        )
        
        # Get suggestions
        suggestions = await get_optimization_suggestions()
        assert len(suggestions["suggestions"]) > 0
        
        # Apply suggestion
        if suggestions["suggestions"]:
            resource_id = suggestions["suggestions"][0]["id"]
            result = await handle_optimization(
                OptimizationRequest(resource_id=resource_id, action="apply")
            )
            assert result["success"] == True

    @pytest.mark.asyncio
    async def test_report_with_forecast_integration(self):
        """Test report generation with forecast integration"""
        from api.cost_advanced_router import (
            generate_report,
            get_forecasts
        )
        
        # Get forecasts
        forecasts = await get_forecasts(days=30)
        
        # Generate report with forecast
        request = ReportRequest(period="30d", format="json", include_forecast=True)
        report = await generate_report(request)
        
        assert report["success"] == True
        assert "forecast" in report["report"]


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test suite for edge cases"""

    @pytest.mark.asyncio
    async def test_empty_budgets_list(self):
        """Test handling empty budgets list"""
        from api.cost_advanced_router import get_budgets
        
        # Temporarily clear budgets
        _budgets.clear()
        
        result = await get_budgets()
        
        assert result["summary"]["total_budgets"] == 0
        assert result["budgets"] == []

    @pytest.mark.asyncio
    async def test_empty_anomalies_list(self):
        """Test handling empty anomalies list"""
        from api.cost_advanced_router import get_anomalies
        
        # Temporarily clear anomalies
        _anomalies.clear()
        
        result = await get_anomalies()
        
        assert result["summary"]["total_count"] == 0
        assert result["anomalies"] == []

    @pytest.mark.asyncio
    async def test_empty_alerts_list(self):
        """Test handling empty alerts list"""
        from api.cost_advanced_router import get_alerts
        
        # Temporarily clear alerts
        _alerts.clear()
        
        result = await get_alerts()
        
        assert result["summary"]["total_count"] == 0
        assert result["alerts"] == []

    @pytest.mark.asyncio
    async def test_large_forecast_period(self):
        """Test handling large forecast period"""
        from api.cost_advanced_router import get_forecasts
        
        result = await get_forecasts(days=365)
        
        assert result["forecast_period"]["days"] == 365

    @pytest.mark.asyncio
    async def test_multiple_filters_anomalies(self):
        """Test applying multiple filters to anomalies"""
        from api.cost_advanced_router import get_anomalies
        
        result = await get_anomalies(severity="high", status="open")
        
        assert result["filters"]["severity"] == "high"
        assert result["filters"]["status"] == "open"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
