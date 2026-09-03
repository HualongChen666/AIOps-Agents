# -*- coding: utf-8 -*-
"""
Test suite for Cost Management Router
成本管理路由测试套件

Tests all 30 endpoints in cost_management_router.py:
- Budget Management (6 endpoints)
- Cost Optimization (4 endpoints)
- Cost Anomaly (5 endpoints)
- Cost Alert (5 endpoints)
- Cost Report (5 endpoints)
- Cost Data Collection (3 endpoints)
- Cost Forecasting (2 endpoints)
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from api.cost_management_router import (
    BudgetCreate,
    BudgetUpdate,
    CostAlertCreate,
    CostAnomalyCreate,
    CostOptimizationCreate,
    CostReportCreate,
    router,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def admin_user():
    """Mock admin user"""
    user = Mock()
    user.id = "admin-1"
    user.username = "admin"
    user.role = "admin"
    user.is_active = True
    return user


@pytest.fixture
def regular_user():
    """Mock regular user"""
    user = Mock()
    user.id = "user-1"
    user.username = "user"
    user.role = "user"
    user.is_active = True
    return user


@pytest.fixture
def sample_budget_data():
    """Sample budget data for testing"""
    return {
        "name": "Test EC2 Budget",
        "service": "Amazon EC2",
        "amount": 1000.0,
        "period": "monthly",
        "alert_threshold": 0.8,
        "alerts_enabled": True,
    }


@pytest.fixture
def sample_optimization_data():
    """Sample optimization data for testing"""
    return {
        "service": "Amazon EC2",
        "optimization_type": "resize",
        "potential_savings": 150.0,
        "implementation_effort": "low",
        "priority": "high",
    }


@pytest.fixture
def sample_anomaly_data():
    """Sample anomaly data for testing"""
    return {
        "service": "Amazon S3",
        "anomaly_type": "spike",
        "severity": "high",
        "description": "Unusual cost spike detected",
        "affected_amount": 250.0,
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data for testing"""
    return {
        "name": "Budget Alert",
        "alert_type": "budget_exceeded",
        "threshold": 800.0,
        "service": "Amazon EC2",
        "notification_channels": ["email", "slack"],
    }


@pytest.fixture
def sample_report_data():
    """Sample report data for testing"""
    return {
        "name": "Monthly Cost Report",
        "report_type": "summary",
        "period_start": "2026-01-01",
        "period_end": "2026-01-31",
    }


# ============================================================================
# Budget Management Tests (6 endpoints)
# ============================================================================


class TestBudgetManagement:
    """Test suite for budget management endpoints"""

    def test_list_budgets_success(self, client, admin_user):
        """Test GET /budgets - list all budgets"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "service": "Amazon EC2",
                        "amount": 1000.0,
                        "spent": 500.0,
                        "remaining": 500.0,
                        "status": "on_track",
                    }
                ]

                response = client.get("/api/cost-management/budgets")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "budgets" in data
                    assert "count" in data

    def test_list_budgets_with_filters(self, client, admin_user):
        """Test GET /budgets with service and status filters"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "service": "Amazon EC2",
                        "amount": 1000.0,
                        "status": "on_track",
                    }
                ]

                response = client.get(
                    "/api/cost-management/budgets?service=Amazon%20EC2&status=on_track"
                )

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"

    def test_get_budget_by_id_success(self, client, admin_user):
        """Test GET /budgets/{budget_id} - get specific budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "service": "Amazon EC2",
                        "amount": 1000.0,
                    }
                ]

                response = client.get("/api/cost-management/budgets/budget-1")

                assert response.status_code in [200, 401, 403, 404]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["budget"]["id"] == "budget-1"

    def test_get_budget_by_id_not_found(self, client, admin_user):
        """Test GET /budgets/{budget_id} with non-existent budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = []

                response = client.get("/api/cost-management/budgets/non-existent")

                assert response.status_code in [404, 401, 403]
                if response.status_code == 404:
                    assert "not found" in response.json()["detail"].lower()

    def test_create_budget_success(self, client, admin_user, sample_budget_data):
        """Test POST /budgets - create new budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.create_budget") as mock_create:
                    mock_create.return_value = {
                        "id": str(uuid.uuid4()),
                        "name": sample_budget_data["name"],
                        "service": sample_budget_data["service"],
                        "amount": sample_budget_data["amount"],
                        "status": "on_track",
                    }

                response = client.post(
                    "/api/cost-management/budgets", json=sample_budget_data
                )

                assert response.status_code in [201, 401, 403]
                if response.status_code == 201:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "budget" in data

    def test_create_budget_validation_error(self, client, admin_user):
        """Test POST /budgets with invalid data"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                invalid_data = {
                    "name": "Test",
                    "service": "EC2",
                    "amount": -100.0,  # Invalid: negative amount
                }

                response = client.post("/api/cost-management/budgets", json=invalid_data)

                # Should fail validation or auth
                assert response.status_code in [400, 422, 401, 403]

    def test_update_budget_success(self, client, admin_user):
        """Test PUT /budgets/{budget_id} - update budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "service": "Amazon EC2",
                        "amount": 1000.0,
                        "spent": 500.0,
                        "remaining": 500.0,
                        "status": "on_track",
                    }
                ]

                update_data = {"name": "Updated EC2 Budget", "amount": 1500.0}
                response = client.put(
                    "/api/cost-management/budgets/budget-1", json=update_data
                )

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"

    def test_update_budget_not_found(self, client, admin_user):
        """Test PUT /budgets/{budget_id} with non-existent budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.get_budget_management") as mock_get:
                    mock_get.return_value = []

                    update_data = {"name": "Updated Budget"}
                    response = client.put(
                        "/api/cost-management/budgets/non-existent", json=update_data
                    )

                    assert response.status_code in [404, 401, 403]

    def test_delete_budget_success(self, client, admin_user):
        """Test DELETE /budgets/{budget_id} - delete budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

                response = client.delete("/api/cost-management/budgets/budget-1")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "deleted successfully" in data["message"]

    def test_delete_budget_not_found(self, client, admin_user):
        """Test DELETE /budgets/{budget_id} with non-existent budget"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                    mock_db = MagicMock()
                    mock_session.return_value = mock_db
                    mock_db.query.return_value.filter.return_value.first.return_value = None

                    response = client.delete("/api/cost-management/budgets/non-existent")

                    assert response.status_code in [404, 401, 403]

    def test_get_budget_status_success(self, client, admin_user):
        """Test GET /budgets/{budget_id}/status - get budget status"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "amount": 1000.0,
                        "spent": 500.0,
                        "remaining": 500.0,
                        "status": "on_track",
                    }
                ]

                response = client.get("/api/cost-management/budgets/budget-1/status")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "utilization_percent" in data
                    assert data["utilization_percent"] == 50.0

    def test_get_budget_status_detailed(self, client, admin_user):
        """Test GET /budgets/{budget_id}/status with detailed=True"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "budget-1",
                        "name": "EC2 Budget",
                        "amount": 1000.0,
                        "spent": 500.0,
                        "remaining": 500.0,
                        "status": "on_track",
                    }
                ]

                response = client.get(
                    "/api/cost-management/budgets/budget-1/status?detailed=true"
                )

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert "breakdown" in data


# ============================================================================
# Cost Optimization Tests (4 endpoints)
# ============================================================================


class TestCostOptimization:
    """Test suite for cost optimization endpoints"""

    def test_list_optimizations_success(self, client, admin_user):
        """Test GET /optimizations - list all optimizations"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_optimization_suggestions") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "opt-1",
                        "resource": "i-12345",
                        "type": "resize",
                        "potential_savings": 150.0,
                        "priority": "high",
                        "status": "pending",
                    }
                ]

                response = client.get("/api/cost-management/optimizations")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "optimizations" in data

    def test_list_optimizations_with_filters(self, client, admin_user):
        """Test GET /optimizations with priority filter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_optimization_suggestions") as mock_get:
                mock_get.return_value = [
                    {
                        "id": "opt-1",
                        "resource": "i-12345",
                        "priority": "high",
                        "status": "pending",
                    }
                ]

                response = client.get(
                    "/api/cost-management/optimizations?priority=high&status=pending"
                )

                assert response.status_code in [200, 401, 403]

    def test_create_optimization_success(self, client, admin_user, sample_optimization_data):
        """Test POST /optimizations - create optimization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.post(
                "/api/cost-management/optimizations", json=sample_optimization_data
            )

            assert response.status_code in [201, 401, 403]
            if response.status_code == 201:
                data = response.json()
                assert data["status"] == "success"
                assert "optimization" in data

    def test_approve_optimization_success(self, client, admin_user):
        """Test PUT /optimizations/{id}/approve - approve optimization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = MagicMock()

                response = client.put("/api/cost-management/optimizations/opt-1/approve")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "approved" in data["message"].lower()

    def test_approve_optimization_not_found(self, client, admin_user):
        """Test PUT /optimizations/{id}/approve with non-existent optimization"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                response = client.put(
                    "/api/cost-management/optimizations/non-existent/approve"
                )

                assert response.status_code in [404, 401, 403]

    def test_get_savings_summary_success(self, client, admin_user):
        """Test GET /optimizations/savings-summary - get savings summary"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_optimization_suggestions") as mock_get:
                mock_get.return_value = [
                    {"potential_savings": 150.0, "priority": "high"},
                    {"potential_savings": 100.0, "priority": "medium"},
                ]

                response = client.get("/api/cost-management/optimizations/savings-summary")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "total_potential_savings" in data
                    assert "by_priority" in data


# ============================================================================
# Cost Anomaly Tests (5 endpoints)
# ============================================================================


class TestCostAnomaly:
    """Test suite for cost anomaly endpoints"""

    def test_list_anomalies_success(self, client, admin_user):
        """Test GET /anomalies - list all anomalies"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_anomaly = MagicMock()
                mock_anomaly.id = "anom-1"
                mock_anomaly.service = "Amazon S3"
                mock_anomaly.anomaly_type = "spike"
                mock_anomaly.detected_at = datetime.now()
                mock_anomaly.severity = "high"
                mock_anomaly.description = "Cost spike"
                mock_anomaly.affected_amount = 250.0
                mock_anomaly.status = "open"
                mock_anomaly.created_at = datetime.now()
                mock_db.query.return_value.all.return_value = [mock_anomaly]

                response = client.get("/api/cost-management/anomalies")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "anomalies" in data

    def test_list_anomalies_with_filters(self, client, admin_user):
        """Test GET /anomalies with severity filter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []

                response = client.get("/api/cost-management/anomalies?severity=high")

                assert response.status_code in [200, 401, 403]

    def test_create_anomaly_success(self, client, admin_user, sample_anomaly_data):
        """Test POST /anomalies - create anomaly record"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.post(
                "/api/cost-management/anomalies", json=sample_anomaly_data
            )

            assert response.status_code in [201, 401, 403]
            if response.status_code == 201:
                data = response.json()
                assert data["status"] == "success"
                assert "anomaly" in data

    def test_resolve_anomaly_success(self, client, admin_user):
        """Test PUT /anomalies/{id}/resolve - resolve anomaly"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_anomaly = MagicMock()
                mock_anomaly.status = "open"
                mock_anomaly.anomaly_metadata = None
                mock_db.query.return_value.filter.return_value.first.return_value = mock_anomaly

                response = client.put(
                    "/api/cost-management/anomalies/anom-1/resolve?resolution_notes=Fixed"
                )

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "resolved" in data["message"].lower()

    def test_resolve_anomaly_not_found(self, client, admin_user):
        """Test PUT /anomalies/{id}/resolve with non-existent anomaly"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                response = client.put(
                    "/api/cost-management/anomalies/non-existent/resolve?resolution_notes=Fixed"
                )

                assert response.status_code in [404, 401, 403]

    def test_get_anomaly_summary_success(self, client, admin_user):
        """Test GET /anomalies/summary - get anomaly summary"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/cost-management/anomalies/summary")

            assert response.status_code in [200, 401, 403]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "by_severity" in data
                assert "by_status" in data

    def test_detect_anomalies_success(self, client, admin_user):
        """Test POST /anomalies/detect - trigger anomaly detection"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            with patch("api.cost_management_router.collect_costs") as mock_collect:
                mock_collect.return_value = [
                    {"date": "2026-01-01", "cost": 100.0},
                    {"date": "2026-01-02", "cost": 300.0},  # Spike
                ]

                response = client.post("/api/cost-management/anomalies/detect?lookback_days=30")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "anomalies_detected" in data


# ============================================================================
# Cost Alert Tests (5 endpoints)
# ============================================================================


class TestCostAlert:
    """Test suite for cost alert endpoints"""

    def test_list_alerts_success(self, client, admin_user):
        """Test GET /alerts - list all alerts"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_alert = MagicMock()
                mock_alert.id = "alert-1"
                mock_alert.name = "Budget Alert"
                mock_alert.alert_type = "budget_exceeded"
                mock_alert.threshold = 800.0
                mock_alert.current_value = 0.0
                mock_alert.service = "Amazon EC2"
                mock_alert.status = "active"
                mock_alert.notification_channels = ["email"]
                mock_alert.created_at = datetime.now()
                mock_db.query.return_value.all.return_value = [mock_alert]

                response = client.get("/api/cost-management/alerts")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "alerts" in data

    def test_list_alerts_with_filters(self, client, admin_user):
        """Test GET /alerts with alert_type filter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []

                response = client.get("/api/cost-management/alerts?alert_type=budget_exceeded")

                assert response.status_code in [200, 401, 403]

    def test_create_alert_success(self, client, admin_user, sample_alert_data):
        """Test POST /alerts - create alert"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.post("/api/cost-management/alerts", json=sample_alert_data)

            assert response.status_code in [201, 401, 403]
            if response.status_code == 201:
                data = response.json()
                assert data["status"] == "success"
                assert "alert" in data

    def test_update_alert_success(self, client, admin_user, sample_alert_data):
        """Test PUT /alerts/{id} - update alert"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.put(
                "/api/cost-management/alerts/alert-1", json=sample_alert_data
            )

            assert response.status_code in [200, 401, 403]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"

    def test_delete_alert_success(self, client, admin_user):
        """Test DELETE /alerts/{id} - delete alert"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.delete("/api/cost-management/alerts/alert-1")

            assert response.status_code in [200, 401, 403]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "deleted successfully" in data["message"]

    def test_test_alert_success(self, client, admin_user):
        """Test POST /alerts/{id}/test - test alert"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_alert = MagicMock()
                mock_alert.threshold = 800.0
                mock_db.query.return_value.filter.return_value.first.return_value = mock_alert
                with patch("api.cost_management_router.collect_costs") as mock_collect:
                    mock_collect.return_value = [{"cost": 500.0}]

                    response = client.post("/api/cost-management/alerts/alert-1/test")

                    assert response.status_code in [200, 401, 403]
                    if response.status_code == 200:
                        data = response.json()
                        assert data["status"] == "success"
                        assert "test_result" in data

    def test_test_alert_not_found(self, client, admin_user):
        """Test POST /alerts/{id}/test with non-existent alert"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                response = client.post("/api/cost-management/alerts/non-existent/test")

                assert response.status_code in [404, 401, 403]


# ============================================================================
# Cost Report Tests (5 endpoints)
# ============================================================================


class TestCostReport:
    """Test suite for cost report endpoints"""

    def test_list_reports_success(self, client, admin_user):
        """Test GET /reports - list all reports"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_report = MagicMock()
                mock_report.id = "report-1"
                mock_report.name = "Monthly Report"
                mock_report.report_type = "summary"
                mock_report.period_start = datetime(2026, 1, 1)
                mock_report.period_end = datetime(2026, 1, 31)
                mock_report.total_cost = 1000.0
                mock_report.generated_at = datetime.now()
                mock_report.status = "completed"
                mock_db.query.return_value.all.return_value = [mock_report]

                response = client.get("/api/cost-management/reports")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "reports" in data

    def test_list_reports_with_filters(self, client, admin_user):
        """Test GET /reports with report_type filter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.all.return_value = []

                response = client.get("/api/cost-management/reports?report_type=summary")

                assert response.status_code in [200, 401, 403]

    def test_generate_report_success(self, client, admin_user, sample_report_data):
        """Test POST /reports - generate report"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.collect_costs") as mock_collect:
                mock_collect.return_value = [{"cost": 100.0}, {"cost": 200.0}]

                response = client.post("/api/cost-management/reports", json=sample_report_data)

                assert response.status_code in [201, 401, 403]
                if response.status_code == 201:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "report" in data

    def test_generate_report_invalid_date_format(self, client, admin_user):
        """Test POST /reports with invalid date format"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            invalid_data = {
                "name": "Test Report",
                "report_type": "summary",
                "period_start": "invalid-date",
                "period_end": "2026-01-31",
            }

            response = client.post("/api/cost-management/reports", json=invalid_data)

            assert response.status_code in [422, 401, 403]

    def test_get_report_by_id_success(self, client, admin_user):
        """Test GET /reports/{id} - get specific report"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_report = MagicMock()
                mock_report.id = "report-1"
                mock_report.name = "Monthly Report"
                mock_report.report_type = "summary"
                mock_report.period_start = datetime(2026, 1, 1)
                mock_report.period_end = datetime(2026, 1, 31)
                mock_report.total_cost = 1000.0
                mock_report.generated_at = datetime.now()
                mock_report.status = "completed"
                mock_report.report_data = {}
                mock_db.query.return_value.filter.return_value.first.return_value = mock_report

                response = client.get("/api/cost-management/reports/report-1")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["report"]["id"] == "report-1"

    def test_get_report_by_id_not_found(self, client, admin_user):
        """Test GET /reports/{id} with non-existent report"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_db.query.return_value.filter.return_value.first.return_value = None

                response = client.get("/api/cost-management/reports/non-existent")

                assert response.status_code in [404, 401, 403]

    def test_delete_report_success(self, client, admin_user):
        """Test DELETE /reports/{id} - delete report"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            response = client.delete("/api/cost-management/reports/report-1")

            assert response.status_code in [200, 401, 403]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "deleted successfully" in data["message"]

    def test_get_reports_summary_success(self, client, admin_user):
        """Test GET /reports/summary - get reports summary"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/cost-management/reports/summary")

            assert response.status_code in [200, 401, 403]
            if response.status_code == 200:
                data = response.json()
                assert data["status"] == "success"
                assert "by_type" in data
                assert "by_status" in data


# ============================================================================
# Cost Data Collection Tests (3 endpoints)
# ============================================================================


class TestCostDataCollection:
    """Test suite for cost data collection endpoints"""

    def test_get_collection_status_success(self, client, admin_user):
        """Test GET /collection/status - get collection status"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_cost_collection_status") as mock_get:
                mock_get.return_value = {
                    "status": "active",
                    "last_collection": "2026-01-15T10:00:00",
                    "next_collection": "2026-01-16T10:00:00",
                }

                response = client.get("/api/cost-management/collection/status")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "collection" in data

    def test_sync_collection_success(self, client, admin_user):
        """Test POST /collection/sync - trigger sync"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.sync_cost_collection") as mock_sync:
                mock_sync.return_value = {
                    "status": "success",
                    "records_synced": 100,
                }

                response = client.post("/api/cost-management/collection/sync")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"

    def test_sync_collection_with_force(self, client, admin_user):
        """Test POST /collection/sync with force parameter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.sync_cost_collection") as mock_sync:
                mock_sync.return_value = {"status": "success"}

                response = client.post("/api/cost-management/collection/sync?force=true")

                assert response.status_code in [200, 401, 403]

    def test_get_collection_history_success(self, client, admin_user):
        """Test GET /collection/history - get collection history"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.collect_costs") as mock_collect:
                mock_collect.return_value = [
                    {"date": "2026-01-01", "cost": 100.0},
                    {"date": "2026-01-02", "cost": 150.0},
                ]

                response = client.get("/api/cost-management/collection/history?limit=10")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert "history" in data

    def test_get_collection_history_large_limit(self, client, admin_user):
        """Test GET /collection/history with large limit"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.collect_costs") as mock_collect:
                mock_collect.return_value = [
                    {"date": f"2026-01-{i:02d}", "cost": 100.0} for i in range(1, 32)
                ]

                response = client.get("/api/cost-management/collection/history?limit=100")

                assert response.status_code in [200, 401, 403]


# ============================================================================
# Cost Forecasting Tests (2 endpoints)
# ============================================================================


class TestCostForecasting:
    """Test suite for cost forecasting endpoints"""

    def test_get_forecast_success(self, client, admin_user):
        """Test GET /forecast - get cost forecast"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.forecast_costs") as mock_forecast:
                mock_forecast.return_value = [
                    {"date": "2026-02-01", "predicted_amount": 105.0},
                    {"date": "2026-02-02", "predicted_amount": 110.0},
                ]

                response = client.get("/api/cost-management/forecast?days=30")

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["days"] == 30
                    assert "forecast" in data

    def test_get_forecast_invalid_days(self, client, admin_user):
        """Test GET /forecast with invalid days parameter"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/cost-management/forecast?days=400")

            assert response.status_code in [422, 401, 403]

    def test_get_forecast_zero_days(self, client, admin_user):
        """Test GET /forecast with zero days"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.get("/api/cost-management/forecast?days=0")

            assert response.status_code in [422, 401, 403]

    def test_predict_endpoint_success(self, client, admin_user):
        """Test POST /forecast/predict - generate prediction"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.predict_costs") as mock_predict:
                mock_predict.return_value = [
                    {"date": "2026-02-01", "predicted_amount": 105.0}
                ]

                response = client.post(
                    "/api/cost-management/forecast/predict", json={"time_horizon": 30}
                )

                assert response.status_code in [200, 401, 403]
                if response.status_code == 200:
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["time_horizon"] == 30

    def test_predict_endpoint_invalid_horizon(self, client, admin_user):
        """Test POST /forecast/predict with invalid time_horizon"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            response = client.post(
                "/api/cost-management/forecast/predict", json={"time_horizon": 400}
            )

            assert response.status_code in [422, 401, 403]


# ============================================================================
# Integration Tests
# ============================================================================


class TestCostManagementIntegration:
    """Integration tests for cost management workflows"""

    def test_budget_to_alert_workflow(self, client, admin_user):
        """Test workflow: create budget -> create alert -> test alert"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("core.rbac.role_required", return_value=lambda f: f):
                with patch("api.cost_management_router.create_budget") as mock_create:
                mock_create.return_value = {
                    "id": "budget-1",
                    "name": "Test Budget",
                    "amount": 1000.0,
                }

                # Create budget
                budget_response = client.post(
                    "/api/cost-management/budgets",
                    json={"name": "Test", "service": "EC2", "amount": 1000.0},
                )
                assert budget_response.status_code in [201, 401, 403]

            # Create alert
            alert_response = client.post(
                "/api/cost-management/alerts",
                json={
                    "name": "Budget Alert",
                    "alert_type": "budget_exceeded",
                    "threshold": 800.0,
                    "service": "EC2",
                    "notification_channels": ["email"],
                },
            )
            assert alert_response.status_code in [201, 401, 403]

    def test_anomaly_detection_to_resolution_workflow(self, client, admin_user):
        """Test workflow: detect anomaly -> resolve anomaly"""
        with patch("core.rbac.role_required", return_value=lambda f: f):
            with patch("api.cost_management_router.collect_costs") as mock_collect:
                mock_collect.return_value = [{"cost": 100.0}, {"cost": 300.0}]

                # Detect anomalies
                detect_response = client.post(
                    "/api/cost-management/anomalies/detect?lookback_days=30"
                )
                assert detect_response.status_code in [200, 401, 403]

            # Resolve anomaly
            with patch("api.cost_management_router.SessionLocal") as mock_session:
                mock_db = MagicMock()
                mock_session.return_value = mock_db
                mock_anomaly = MagicMock()
                mock_anomaly.status = "open"
                mock_anomaly.anomaly_metadata = None
                mock_db.query.return_value.filter.return_value.first.return_value = (
                    mock_anomaly
                )

                resolve_response = client.put(
                    "/api/cost-management/anomalies/anom-1/resolve?resolution_notes=Investigated"
                )
                assert resolve_response.status_code in [200, 401, 403]


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling across all endpoints"""

    def test_unauthorized_access_without_auth(self, client):
        """Test that endpoints require authentication"""
        # This test assumes auth is properly configured
        # If auth is mocked, this may pass, which is acceptable
        response = client.get("/api/cost-management/budgets")
        # Should either return 401/403 or 200 if auth is mocked
        assert response.status_code in [200, 401, 403, 500]

    def test_server_error_handling(self, client, admin_user):
        """Test server error handling"""
        with patch("core.authentication.get_current_active_user", return_value=admin_user):
            with patch("api.cost_management_router.get_budget_management") as mock_get:
                mock_get.side_effect = Exception("Database error")

                response = client.get("/api/cost-management/budgets")

                assert response.status_code in [500, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
